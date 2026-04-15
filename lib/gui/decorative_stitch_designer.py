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


REPEAT_COUNT = 4
PREVIEW_MARGIN = 20


class PatternPreviewPanel(wx.Panel):
    """Live preview showing the pattern tiling across multiple repeats."""

    def __init__(self, parent):
        super().__init__(parent, style=wx.BORDER_SIMPLE)
        self.SetMinSize((250, -1))
        self.SetBackgroundColour(wx.WHITE)
        self.points = []
        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SIZE, self._on_size)

    def _on_size(self, event):
        self.Refresh()
        event.Skip()

    def set_points(self, points):
        self.points = list(points)
        self.Refresh()

    def _on_paint(self, event):
        dc = wx.PaintDC(self)
        dc.Clear()

        if len(self.points) < 2:
            return

        dx = self.points[-1][0] - self.points[0][0]
        dy = self.points[-1][1] - self.points[0][1]

        # Build all repeated points to determine bounding box
        all_repeated = []
        for r in range(REPEAT_COUNT):
            for x, y in self.points:
                all_repeated.append((x + r * dx, y + r * dy))

        min_x = min(p[0] for p in all_repeated)
        max_x = max(p[0] for p in all_repeated)
        min_y = min(p[1] for p in all_repeated)
        max_y = max(p[1] for p in all_repeated)

        w, h = self.GetClientSize()
        span_x = max_x - min_x or 1
        span_y = max_y - min_y or 1
        scale = min(
            (w - 2 * PREVIEW_MARGIN) / span_x,
            (h - 2 * PREVIEW_MARGIN) / span_y,
        )

        def to_screen(x, y):
            sx = PREVIEW_MARGIN + (x - min_x) * scale
            sy = PREVIEW_MARGIN + (y - min_y) * scale
            return int(sx), int(sy)

        # Draw each repeat
        for r in range(REPEAT_COUNT):
            shifted = [(x + r * dx, y + r * dy) for x, y in self.points]
            screen = [to_screen(x, y) for x, y in shifted]

            dc.SetPen(wx.Pen(wx.Colour(50, 50, 200), 1))
            for i in range(len(screen) - 1):
                dc.DrawLine(screen[i][0], screen[i][1], screen[i + 1][0], screen[i + 1][1])

            # Interior points (not the anchors shared between repeats)
            dc.SetBrush(wx.Brush(wx.Colour(50, 50, 200)))
            dc.SetPen(wx.Pen(wx.Colour(20, 20, 140), 1))
            for i in range(1, len(screen) - 1):
                dc.DrawCircle(screen[i][0], screen[i][1], 3)

            # Join node: last point of this repeat (= first of next)
            jx, jy = screen[-1]
            dc.SetBrush(wx.Brush(wx.Colour(60, 140, 60)))
            dc.SetPen(wx.Pen(wx.Colour(30, 90, 30), 1))
            dc.DrawCircle(jx, jy, 5)

        # First anchor of the whole chain
        fx, fy = to_screen(self.points[0][0], self.points[0][1])
        dc.SetBrush(wx.Brush(wx.Colour(60, 140, 60)))
        dc.SetPen(wx.Pen(wx.Colour(30, 90, 30), 1))
        dc.DrawCircle(fx, fy, 5)


class PointListPanel(wx.Panel):
    """Ordered list of points synced with the canvas."""

    def __init__(self, parent, on_selection_changed=None, on_coord_changed=None):
        super().__init__(parent)
        self.SetMinSize((180, -1))
        self.on_selection_changed = on_selection_changed
        self.on_coord_changed = on_coord_changed
        self._points = []
        self._updating = False

        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, label=_("Points"))
        sizer.Add(label, 0, wx.ALL, 5)

        self.listbox = wx.ListBox(self, style=wx.LB_SINGLE)
        self.listbox.Bind(wx.EVT_LISTBOX, self._on_select)
        sizer.Add(self.listbox, 1, wx.EXPAND | wx.ALL, 5)

        coord_grid = wx.FlexGridSizer(rows=2, cols=2, hgap=5, vgap=4)
        coord_grid.AddGrowableCol(1)
        coord_grid.Add(wx.StaticText(self, label="X:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.x_ctrl = wx.SpinCtrlDouble(self, min=-9999, max=9999, inc=1)
        self.x_ctrl.SetDigits(1)
        coord_grid.Add(self.x_ctrl, 1, wx.EXPAND)
        coord_grid.Add(wx.StaticText(self, label="Y:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self.y_ctrl = wx.SpinCtrlDouble(self, min=-9999, max=9999, inc=1)
        self.y_ctrl.SetDigits(1)
        coord_grid.Add(self.y_ctrl, 1, wx.EXPAND)
        sizer.Add(coord_grid, 0, wx.EXPAND | wx.ALL, 5)

        self.x_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_coord_edit)
        self.y_ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self._on_coord_edit)
        self.x_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_coord_edit)
        self.y_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_coord_edit)

        self.x_ctrl.Enable(False)
        self.y_ctrl.Enable(False)

        self.SetSizer(sizer)

    def set_points(self, points, selected_index=None):
        self._points = list(points)
        current_selection = self.listbox.GetSelection()
        self._updating = True
        self.listbox.Clear()
        for i, (x, y) in enumerate(points):
            self.listbox.Append(f"{i}: ({x:.1f}, {y:.1f})")
        if selected_index is not None and 0 <= selected_index < len(points):
            self.listbox.SetSelection(selected_index)
        elif current_selection != wx.NOT_FOUND and current_selection < len(points):
            self.listbox.SetSelection(current_selection)
            selected_index = current_selection
        self._updating = False
        self._update_coord_fields(selected_index)

    def _update_coord_fields(self, index):
        last = len(self._points) - 1
        is_anchor = index is None or index == 0 or index == last
        if index is not None and 0 <= index < len(self._points):
            x, y = self._points[index]
            self._updating = True
            self.x_ctrl.SetValue(x)
            self.y_ctrl.SetValue(y)
            self._updating = False
        self.x_ctrl.Enable(not is_anchor)
        self.y_ctrl.Enable(not is_anchor)

    def _on_select(self, event):
        idx = self.listbox.GetSelection()
        if idx != wx.NOT_FOUND:
            self._update_coord_fields(idx)
            if self.on_selection_changed:
                self.on_selection_changed(idx)

    def _on_coord_edit(self, event):
        if self._updating:
            return
        idx = self.listbox.GetSelection()
        if idx == wx.NOT_FOUND:
            return
        last = len(self._points) - 1
        if idx == 0 or idx == last:
            return
        x = self.x_ctrl.GetValue()
        y = self.y_ctrl.GetValue()
        if self.on_coord_changed:
            self.on_coord_changed(idx, x, y)


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
            on_coord_changed=self._on_coord_changed,
        )

        self.canvas = DesignerCanvas(
            main_panel,
            on_points_changed=self._on_points_changed,
        )

        self.preview = PatternPreviewPanel(main_panel)

        main_sizer.Add(self.list_panel, 0, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(self.canvas, 1, wx.EXPAND | wx.ALL, 5)
        main_sizer.Add(self.preview, 1, wx.EXPAND | wx.ALL, 5)

        main_panel.SetSizer(main_sizer)

        frame_sizer = wx.BoxSizer(wx.VERTICAL)
        frame_sizer.Add(main_panel, 1, wx.EXPAND)
        self.SetSizer(frame_sizer)

        self.list_panel.set_points(self.canvas.points)
        self.preview.set_points(self.canvas.points)

        self.Fit()
        self.Layout()

    def _on_points_changed(self, points, selected_index):
        self.list_panel.set_points(points, selected_index)
        self.preview.set_points(points)

    def _on_list_selection(self, index):
        self.canvas.set_selected(index)

    def _on_coord_changed(self, index, x, y):
        self.canvas.points[index] = (x, y)
        self.canvas.Refresh()
        self.list_panel.set_points(self.canvas.points, index)
        self.preview.set_points(self.canvas.points)


def open_decorative_designer():
    frame = DecorativeDesignerFrame()
    frame.Show()
