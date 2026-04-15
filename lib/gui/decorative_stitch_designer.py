# Authors: see git history
#
# Copyright (c) 2026 Authors
# Licensed under the GNU GPL version 3.0 or later.  See the file LICENSE for details.

import math

import wx

from ..i18n import _

HIT_RADIUS = 8


def _point_to_segment_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    seg_len_sq = dx * dx + dy * dy
    if seg_len_sq == 0:
        return math.hypot(px - ax, py - ay), 0.0
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg_len_sq))
    cx = ax + t * dx
    cy = ay + t * dy
    return math.hypot(px - cx, py - cy), t


class DesignerCanvas(wx.Panel):
    """Canvas for editing the decorative stitch line."""

    def __init__(self, parent, on_points_changed=None):
        super().__init__(parent, style=wx.BORDER_SIMPLE)
        self.SetMinSize((400, 300))
        self.SetBackgroundColour(wx.WHITE)

        self.points = [(200.0, 50.0), (200.0, 250.0)]
        self.selected_index = None
        self.dragging_index = None
        self.on_points_changed = on_points_changed

        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_left_down)
        self.Bind(wx.EVT_LEFT_UP, self._on_left_up)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_SIZE, self._on_size)

    def _on_size(self, event):
        self.Refresh()
        event.Skip()

    def _on_paint(self, event):
        dc = wx.PaintDC(self)
        dc.Clear()

        if len(self.points) < 2:
            return

        dc.SetPen(wx.Pen(wx.Colour(50, 50, 200), 2))
        for i in range(len(self.points) - 1):
            ax, ay = self.points[i]
            bx, by = self.points[i + 1]
            dc.DrawLine(int(ax), int(ay), int(bx), int(by))

        last = len(self.points) - 1
        for i, (x, y) in enumerate(self.points):
            is_anchor = (i == 0 or i == last)
            if i == self.selected_index:
                dc.SetBrush(wx.Brush(wx.Colour(255, 100, 0)))
                dc.SetPen(wx.Pen(wx.Colour(180, 60, 0), 2))
                radius = 7
            elif is_anchor:
                dc.SetBrush(wx.Brush(wx.Colour(60, 140, 60)))
                dc.SetPen(wx.Pen(wx.Colour(30, 90, 30), 2))
                radius = 7
            else:
                dc.SetBrush(wx.Brush(wx.Colour(50, 50, 200)))
                dc.SetPen(wx.Pen(wx.Colour(20, 20, 140), 1))
                radius = 5
            dc.DrawCircle(int(x), int(y), radius)

    def _on_left_down(self, event):
        mx, my = event.GetX(), event.GetY()

        # Drag existing point if near enough
        last = len(self.points) - 1
        for i, (px, py) in enumerate(self.points):
            if math.hypot(mx - px, my - py) <= HIT_RADIUS:
                self.selected_index = i
                if i != 0 and i != last:
                    self.dragging_index = i
                    self.CaptureMouse()
                self._notify_changed()
                self.Refresh()
                return

        best_dist = HIT_RADIUS + 1
        best_seg = None
        for i in range(len(self.points) - 1):
            ax, ay = self.points[i]
            bx, by = self.points[i + 1]
            dist, _t = _point_to_segment_dist(mx, my, ax, ay, bx, by)
            if dist < best_dist:
                best_dist = dist
                best_seg = i

        # Add new point on found segment
        if best_seg is not None:
            new_point = (float(mx), float(my))
            self.points.insert(best_seg + 1, new_point)
            self.selected_index = best_seg + 1
            self.dragging_index = best_seg + 1
            self.CaptureMouse()
            self._notify_changed()
            self.Refresh()

    def _on_left_up(self, event):
        if self.dragging_index is not None:
            self.dragging_index = None
            if self.HasCapture():
                self.ReleaseMouse()
            self.Refresh()

    def _on_motion(self, event):
        if self.dragging_index is not None and event.Dragging() and event.LeftIsDown():
            mx, my = event.GetX(), event.GetY()
            self.points[self.dragging_index] = (float(mx), float(my))
            self._notify_changed()
            self.Refresh()

    def _notify_changed(self):
        if self.on_points_changed:
            self.on_points_changed(self.points, self.selected_index)

    def set_selected(self, index):
        self.selected_index = index
        self.Refresh()


class PointListPanel(wx.Panel):
    """Ordered list of points synced with the canvas."""

    def __init__(self, parent, on_selection_changed=None):
        super().__init__(parent)
        self.SetMinSize((180, -1))
        self.on_selection_changed = on_selection_changed

        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, label=_("Points"))
        sizer.Add(label, 0, wx.ALL, 5)

        self.listbox = wx.ListBox(self, style=wx.LB_SINGLE)
        self.listbox.Bind(wx.EVT_LISTBOX, self._on_select)
        sizer.Add(self.listbox, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(sizer)

    def set_points(self, points, selected_index=None):
        current_selection = self.listbox.GetSelection()
        self.listbox.Clear()
        for i, (x, y) in enumerate(points):
            self.listbox.Append(f"{i}: ({x:.1f}, {y:.1f})")
        if selected_index is not None and 0 <= selected_index < len(points):
            self.listbox.SetSelection(selected_index)
        elif current_selection != wx.NOT_FOUND and current_selection < len(points):
            self.listbox.SetSelection(current_selection)

    def _on_select(self, event):
        idx = self.listbox.GetSelection()
        if idx != wx.NOT_FOUND and self.on_selection_changed:
            self.on_selection_changed(idx)


class DecorativeDesignerFrame(wx.Frame):
    """Main window for the decorative stitch designer."""

    def __init__(self):
        parent = wx.GetApp().GetTopWindow()
        super().__init__(
            parent,
            wx.ID_ANY,
            _("Decorative Stitch Designer"),
            style=wx.DEFAULT_FRAME_STYLE | (wx.FRAME_FLOAT_ON_PARENT if parent else 0),
        )
        self.SetMinSize((620, 380))

        main_panel = wx.Panel(self)
        main_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.list_panel = PointListPanel(
            main_panel,
            on_selection_changed=self._on_list_selection,
        )

        self.canvas = DesignerCanvas(
            main_panel,
            on_points_changed=self._on_points_changed,
        )

        main_sizer.Add(self.list_panel, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)

        main_panel.SetSizer(main_sizer)

        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(main_panel, 1, wx.EXPAND)
        self.SetSizer(frame_sizer)

        self.list_panel.set_points(self.canvas.points)

        self.Fit()
        self.Layout()

    def _on_points_changed(self, points, selected_index):
        self.list_panel.set_points(points, selected_index)

    def _on_list_selection(self, index):
        self.canvas.set_selected(index)


def open_decorative_designer():
    frame = DecorativeDesignerFrame()
    frame.Show()
