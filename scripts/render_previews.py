#!/usr/bin/env python3
"""Render PNG previews of the CadQuery model for the docs and the Pages site (VTK, offscreen).

These are pictures of the MODEL, with idealised glowing numerals. They are not photos of a
built clock. Usage: python3 scripts/render_previews.py   (writes docs/img/*.png)
"""
import sys
from pathlib import Path

import vtk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
import build_cad as B  # noqa: E402

OUT = ROOT / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)
BG = (0.078, 0.067, 0.059)
PEEL = False  # depth peeling showed translucent parts through opaque walls on the headless renderer


def actor_from_shape(shape, color, opacity=1.0, tol=0.08, specular=0.15, emissive=False):
    pd = shape.val().toVtkPolyData(tol, 0.08)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(pd)
    normals.SetFeatureAngle(35)
    normals.SplittingOn()
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(normals.GetOutputPort())
    m.ScalarVisibilityOff()
    a = vtk.vtkActor()
    a.SetMapper(m)
    p = a.GetProperty()
    p.SetColor(*color)
    p.SetOpacity(opacity)
    p.SetSpecular(specular)
    p.SetSpecularPower(30)
    p.SetAmbient(0.18)
    if emissive:
        p.SetAmbient(1.0)
        p.SetDiffuse(0.0)
    return a


def digit_actor(ch, x, y, z, height=17.0):
    t = vtk.vtkVectorText()
    t.SetText(ch)
    t.Update()
    b = t.GetOutput().GetBounds()
    tf = vtk.vtkTransform()
    tf.Translate(x, y, z)
    tf.RotateX(90)
    s = height / (b[3] - b[2])
    tf.Scale(s, s, s)
    tf.Translate(-(b[0] + b[1]) / 2, -(b[2] + b[3]) / 2, 0)
    f = vtk.vtkTransformPolyDataFilter()
    f.SetTransform(tf)
    f.SetInputConnection(t.GetOutputPort())
    tube = vtk.vtkTubeFilter()   # give the strokes a little body, like a glowing cathode wire
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(f.GetOutputPort())
    a = vtk.vtkActor()
    a.SetMapper(m)
    p = a.GetProperty()
    p.SetColor(1.0, 0.52, 0.12)
    p.SetAmbient(1.0)
    p.SetDiffuse(0.0)
    return a


def render(actors, path, cam_pos, focal, size=(1600, 820), view_angle=24, caption=None):
    r = vtk.vtkRenderer()
    r.SetBackground(*BG)
    r.SetUseDepthPeeling(int(PEEL))
    r.SetMaximumNumberOfPeels(40)
    r.SetOcclusionRatio(0.0)
    for a in actors:
        r.AddActor(a)
    key = vtk.vtkLight()
    key.SetPosition(-200, -300, 400)
    key.SetFocalPoint(*focal)
    key.SetIntensity(0.85)
    fill = vtk.vtkLight()
    fill.SetPosition(500, -100, 150)
    fill.SetFocalPoint(*focal)
    fill.SetIntensity(0.35)
    rim = vtk.vtkLight()
    rim.SetPosition(117, 400, 250)
    rim.SetFocalPoint(*focal)
    rim.SetIntensity(0.4)
    for L in (key, fill, rim):
        L.SetLightTypeToSceneLight()
        r.AddLight(L)
    cam = r.GetActiveCamera()
    cam.SetPosition(*cam_pos)
    cam.SetFocalPoint(*focal)
    cam.SetViewUp(0, 0, 1)
    cam.SetViewAngle(view_angle)
    if caption:
        txt = vtk.vtkTextActor()
        txt.SetInput(caption)
        tp = txt.GetTextProperty()
        tp.SetFontSize(20)
        tp.SetColor(0.96, 0.91, 0.86)
        txt.SetDisplayPosition(24, size[1] - 40)
        r.AddActor2D(txt)
        note = vtk.vtkTextActor()
        note.SetInput("CadQuery model render - not a photo of a built clock")
        note.GetTextProperty().SetFontSize(14)
        note.GetTextProperty().SetColor(0.54, 0.48, 0.42)
        note.SetDisplayPosition(24, 16)
        r.AddActor2D(note)
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetAlphaBitPlanes(1)
    rw.SetMultiSamples(0)
    rw.AddRenderer(r)
    rw.SetSize(*size)
    rw.Render()
    w = vtk.vtkWindowToImageFilter()
    w.SetInput(rw)
    w.SetScale(1)
    w.Update()
    pw = vtk.vtkPNGWriter()
    pw.SetFileName(str(path))
    pw.SetInputConnection(w.GetOutputPort())
    pw.Write()


def scene(env, digits="100842", panel_opacity=0.38, z_chassis=0.0, z_shell=0.0, z_rods=0.0, y_panel=0.0, shell=True, panel=True, rods=True):
    dark = (0.13, 0.13, 0.14)
    mv = lambda shp, z: shp.translate((0, 0, z)) if z else shp
    acts = []
    for k, v in env.items():
        col, op, em, spec = {"PCB": ((0.05, 0.28, 0.11), 1, False, 0.15), "glass": ((1.0, 0.8, 0.6), 0.16, False, 0.9),
                             "spacer": ((0.1, 0.1, 0.1), 1, False, 0.15), "lamp": ((1.0, 0.45, 0.1), 0.95, True, 0.15),
                             "button": ((0.35, 0.35, 0.36), 1, False, 0.15)}[k.split("_")[0]]
        acts.append(actor_from_shape(mv(v, z_chassis), col, op, specular=spec, emissive=em))
    acts.append(actor_from_shape(mv(B.bottom_cover(), z_chassis), (0.2, 0.2, 0.21)))
    acts.append(actor_from_shape(mv(B.cable_clamp(), z_chassis), (0.85, 0.52, 0.22)))
    zdig = B.PCB_TOP_Z + B.SPACER_H + 24 + z_chassis
    acts += [digit_actor(ch, x, y, zdig) for ch, (x, y) in zip(digits, B.TUBES)]
    for x, y in (B.BUTTONS.values() if rods else []):
        acts.append(actor_from_shape(mv(B.button_rod(x, y), z_rods), (0.24, 0.24, 0.25), specular=0.3))  # printed in the case colour
    if shell:
        acts.append(actor_from_shape(mv(B.case_shell(), z_shell), dark, specular=0.12))
    if panel:
        acts.append(actor_from_shape(B.window_panel().translate((0, y_panel, 0)), (0.3, 0.26, 0.22), panel_opacity, specular=1.0))
    return acts


def main():
    env = B.pcb_mechanical()
    for old in ("hero_all_printed.png", "hero_clear_top.png", "hood_underside.png", "frame_from_above.png", "part_02_bottom_cover.png"):
        (OUT / old).unlink(missing_ok=True)
    render(scene(env), OUT / "hero_alarm_clock.png", (117 + 150, -390, 210), (117, 40, 52), view_angle=27,
           caption="Rev C alarm-clock case: fully enclosed, smoked window (model)")
    render(scene(env, panel_opacity=0.3), OUT / "hero_front.png", (117, -470, 70), (117, 40, 54), view_angle=24,
           caption="Front view (model)")
    render(scene(env, shell=False, panel=False, rods=False), OUT / "chassis.png", (117 + 160, -330, 220), (117, 40, 35), view_angle=27,
           caption="Chassis: floor + PCB + tubes, case removed (model)")
    shell = actor_from_shape(B.case_shell().rotate((117, 40, 56), (118, 40, 56), 180), (0.6, 0.6, 0.63))
    render([shell], OUT / "case_underside.png", (117 + 230, -330, 520), (117, 40, 60),
           caption="01 case from below: window slot rails, button guides, corner blocks")
    for name in ("02_floor", "03_cable_clamp", "04_button_rod", "06_fit_coupon", "07_unpowered_lead_pattern_coupon"):
        fn, flip, _ = B.PARTS[name]
        s = B.print_orient(fn(), flip)
        bb = s.val().BoundingBox()
        c = ((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, bb.zmax / 2)
        d = max(bb.xlen, bb.ylen, bb.zlen) * 1.9
        render([actor_from_shape(s, (0.85, 0.52, 0.22), specular=0.2)], OUT / f"part_{name}.png",
               (c[0] + d * 0.45, c[1] - d, c[2] + d * 0.8), c, size=(900, 560), caption=f"{name} (print orientation)")
    exploded(env)
    print("wrote previews to docs/img/")


def label3d(text, pos, color=(0.96, 0.91, 0.86)):
    a = vtk.vtkBillboardTextActor3D()
    a.SetInput(text)
    a.SetPosition(*pos)
    tp = a.GetTextProperty()
    tp.SetFontSize(22)
    tp.SetColor(*color)
    tp.SetJustificationToLeft()
    return a


def exploded(env):
    """Exploded view: chassis (floor + PCB + tubes), window panel, case and button rods pulled apart."""
    z_shell, z_rods, y_panel = 135, 200, -95
    acts = scene(env, z_shell=z_shell, z_rods=z_rods, y_panel=y_panel, panel_opacity=0.55)
    xl = B.L + 12
    acts += [label3d("2  chassis: floor + PCB + tubes (5x M2x6)", (xl, 40, 10)),
             label3d("1  smoked acrylic window slides into the case", (B.PANEL_X1 - 30, y_panel, -2)),
             label3d("3  case lowers over (4x M2x8 from below)", (xl, 40, z_shell + 60)),
             label3d("4  button rods drop into the top", (xl, 40, z_rods + 100))]
    render(acts, OUT / "exploded.png", (117 + 420, -640, 420), (180, 10, 130), size=(1600, 1150), view_angle=30,
           caption="Exploded view: numbers show the assembly order (model)")


if __name__ == "__main__":
    main()
