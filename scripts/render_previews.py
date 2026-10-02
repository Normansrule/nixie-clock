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
    r.SetUseDepthPeeling(1)
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


def main():
    env = B.pcb_mechanical()
    dark = (0.13, 0.13, 0.14)
    glass = [actor_from_shape(v, (1.0, 0.8, 0.6), 0.16, specular=0.9) for k, v in env.items() if k.startswith("glass")]
    lamps = [actor_from_shape(v, (1.0, 0.45, 0.1), 0.95, emissive=True) for k, v in env.items() if k.startswith("lamp")]
    spacers = [actor_from_shape(v, (0.1, 0.1, 0.1)) for k, v in env.items() if k.startswith("spacer")]
    buttons = [actor_from_shape(v, (0.35, 0.35, 0.36)) for k, v in env.items() if k.startswith("button")]
    pcb = actor_from_shape(env["PCB"], (0.05, 0.22, 0.1))
    zdig = B.PCB_TOP_Z + B.SPACER_H + 24
    digits = [digit_actor(ch, x, y, zdig) for ch, (x, y) in zip("123456", B.TUBES)]
    floor = actor_from_shape(B.bottom_cover(), dark)
    hood = actor_from_shape(B.printed_hood(), dark, specular=0.08)
    frame = actor_from_shape(B.acrylic_frame(), dark, specular=0.08)
    acrylic = actor_from_shape(B.top_plate(), (0.8, 0.92, 1.0), 0.22, specular=1.0)

    front = ((117 + 95, -420, 190), (117, 38, 42))
    render([floor, hood] + buttons + lamps + digits + glass, OUT / "hero_all_printed.png", *front,
           caption="Rev C - all-printed hood (model)")
    render([floor, frame, pcb] + spacers + buttons + lamps + digits + [acrylic] + glass, OUT / "hero_clear_top.png", *front,
           caption="Rev C - printed frame + 3 mm clear cast-acrylic top (model)")
    render([actor_from_shape(B.printed_hood(), (0.6, 0.6, 0.63))], OUT / "hood_underside.png",
           (117 + 120, -260, -260), (117, 40, 15), caption="01 printed hood from below: baffle collars, PCB posts, corner blocks, button pockets")
    render([actor_from_shape(B.acrylic_frame(), (0.6, 0.6, 0.63))], OUT / "frame_from_above.png",
           (117 + 60, -200, 360), (117, 40, 10), caption="04 acrylic frame: chamfered seat ledge, corner blocks, PCB bosses")
    for name in ("02_bottom_cover", "03_cable_clamp", "06_fit_coupon", "07_unpowered_lead_pattern_coupon"):
        fn, flip = B.PARTS[name]
        s = B.print_orient(fn(), flip)
        bb = s.val().BoundingBox()
        c = ((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, bb.zmax / 2)
        d = max(bb.xlen, bb.ylen) * 1.9
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
    """Exploded clear-top assembly: floor, frame, PCB with tubes, acrylic, each lifted apart."""
    dz = {"floor": -55, "clamp": -55, "frame": 0, "pcb": 52, "acrylic": 78}
    dark = (0.16, 0.16, 0.17)
    mv = lambda shape, z: shape.translate((0, 0, z))
    acts = [actor_from_shape(mv(B.bottom_cover(), dz["floor"]), dark),
            actor_from_shape(mv(B.cable_clamp(), dz["clamp"]), (0.85, 0.52, 0.22)),
            actor_from_shape(mv(B.acrylic_frame(), dz["frame"]), dark, specular=0.08),
            actor_from_shape(mv(B.top_plate(), dz["acrylic"]), (0.8, 0.92, 1.0), 0.3, specular=1.0)]
    for k, v in env.items():
        col, op, em = {"PCB": ((0.05, 0.3, 0.12), 1, False), "glass": ((1.0, 0.8, 0.6), 0.2, False), "spacer": ((0.1, 0.1, 0.1), 1, False),
                       "lamp": ((1.0, 0.45, 0.1), 0.95, True), "button": ((0.35, 0.35, 0.36), 1, False)}[k.split("_")[0]]
        acts.append(actor_from_shape(mv(v, dz["pcb"]), col, op, emissive=em))
    zdig = B.PCB_TOP_Z + B.SPACER_H + 24 + dz["pcb"]
    acts += [digit_actor(ch, x, y, zdig) for ch, (x, y) in zip("123456", B.TUBES)]
    xl = B.BASE_L + 14
    acts += [label3d("02 bottom cover + 03 cable clamp  (4x M2x8)", (xl, 40, dz["floor"] + 2)),
             label3d("04 printed frame (PETG)", (xl, 40, dz["frame"] + 14)),
             label3d("PCB 218x64 mm + 6x IN-14 + 2x NE-2  (5x M2x4)", (xl, 40, dz["pcb"] + 22)),
             label3d("3 mm clear cast acrylic top  (4x M2x6)", (xl, 40, dz["acrylic"] + 30))]
    render(acts, OUT / "exploded.png", (117 + 330, -520, 330), (175, 40, 20), size=(1600, 1000), view_angle=26,
           caption="Exploded view - clear-top option (model)")


if __name__ == "__main__":
    main()
