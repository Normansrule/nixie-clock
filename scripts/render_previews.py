#!/usr/bin/env python3
"""Render PNG previews of the CadQuery model for the docs and the Pages site (VTK, offscreen).

These are pictures of the MODEL, with idealised glowing numerals. They are not photos of a
built clock. Usage: python3 scripts/render_previews.py   (writes docs/img/*.png)
"""
import sys
from pathlib import Path

import math

import numpy as np
import vtk
from vtk.util import numpy_support

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source"))
import build_cad as B  # noqa: E402

OUT = ROOT / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)
BG = (0.078, 0.067, 0.059)
PEEL = False  # depth peeling showed translucent parts through opaque walls on the headless renderer


WALNUT_SPAN = 254.0   # mm of board covered by one texture repeat along the grain


def _smooth_noise(rng, shape, scale_u, scale_v):
    """Cheap value noise: random grid, bilinearly upsampled."""
    gu, gv = max(2, shape[1] // scale_u + 2), max(2, shape[0] // scale_v + 2)
    g = rng.standard_normal((gv, gu))
    v = np.linspace(0, gv - 1.001, shape[0])
    u = np.linspace(0, gu - 1.001, shape[1])
    v0, u0 = v.astype(int), u.astype(int)
    fv, fu = (v - v0)[:, None], (u - u0)[None, :]
    fv, fu = fv * fv * (3 - 2 * fv), fu * fu * (3 - 2 * fu)
    a, b = g[v0][:, u0], g[v0][:, u0 + 1]
    c, d = g[v0 + 1][:, u0], g[v0 + 1][:, u0 + 1]
    return (a * (1 - fu) + b * fu) * (1 - fv) + (c * (1 - fu) + d * fu) * fv


def walnut_texture(seed=7, w=2048, h=1024):
    """Procedural black-walnut grain (grain runs along u). Returns a vtkTexture."""
    rng = np.random.default_rng(seed)
    vv = np.linspace(0, 1, h)[:, None] * np.ones((1, w))
    warp = 0.5 * _smooth_noise(rng, (h, w), 1500, 320) + 0.12 * _smooth_noise(rng, (h, w), 260, 90)
    spacing = 1.0 + 0.35 * _smooth_noise(rng, (h, w), 2000, 700)
    rings = vv * 20 * spacing + warp
    band = (0.5 + 0.5 * np.sin(2 * np.pi * rings)) ** 1.6
    streak = 0.5 + 0.5 * np.tanh(1.2 * _smooth_noise(rng, (h, w), 1400, 14))
    figure = 0.5 + 0.5 * np.tanh(1.0 * _smooth_noise(rng, (h, w), 700, 440))
    pores = rng.random((h, w))
    k = 41
    pores = np.cumsum(pores, axis=1)
    pores = (pores[:, k:] - pores[:, :-k]) / k
    pores = np.pad(pores, ((0, 0), (k // 2, k - k // 2)), mode="edge")
    pores = (pores - pores.mean()) * 9
    light = np.array([0.44, 0.285, 0.17])
    dark = np.array([0.205, 0.115, 0.07])
    t = np.clip(0.38 * band + 0.27 * streak + 0.25 * figure + 0.10 * pores, 0, 1)[..., None]
    rgb = dark + (light - dark) * t
    img = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
    data = vtk.vtkImageData()
    data.SetDimensions(w, h, 1)
    arr = numpy_support.numpy_to_vtk(img.reshape(-1, 3), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
    arr.SetNumberOfComponents(3)
    data.GetPointData().SetScalars(arr)
    tex = vtk.vtkTexture()
    tex.SetInputData(data)
    tex.InterpolateOn()
    tex.RepeatOn()
    tex.MipmapOn()
    return tex


_TEX = {}


def wood_actor(shape, axis_u, axis_v, origin, tex_seed=7):
    """Textured hardwood: the grain runs along axis_u ('x', 'y' or 'z')."""
    if tex_seed not in _TEX:
        _TEX[tex_seed] = walnut_texture(tex_seed)
    pd = shape.val().toVtkPolyData(0.05, 0.08)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(pd)
    normals.SetFeatureAngle(35)
    normals.SplittingOn()
    unit = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
    o = np.array(origin, float)
    tm = vtk.vtkTextureMapToPlane()
    tm.SetInputConnection(normals.GetOutputPort())
    tm.SetOrigin(*o)
    tm.SetPoint1(*(o + WALNUT_SPAN * np.array(unit[axis_u])))
    tm.SetPoint2(*(o + WALNUT_SPAN / 2 * np.array(unit[axis_v])))   # 127 mm: taller than any board, so no seam
    tm.AutomaticPlaneGenerationOff()
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(tm.GetOutputPort())
    m.ScalarVisibilityOff()
    a = vtk.vtkActor()
    a.SetMapper(m)
    a.SetTexture(_TEX[tex_seed])
    pr = a.GetProperty()
    pr.SetColor(1, 1, 1)
    pr.SetAmbient(0.22)
    pr.SetDiffuse(0.85)
    pr.SetSpecular(0.22)        # oiled finish: soft sheen
    pr.SetSpecularPower(18)
    pr.SetSpecularColor(1.0, 0.9, 0.8)
    return a


def brass_actor(shape):
    a = actor_from_shape(shape, (0.80, 0.60, 0.28), specular=0.9)
    pr = a.GetProperty()
    pr.SetSpecularPower(55)
    pr.SetSpecularColor(1.0, 0.88, 0.62)
    pr.SetDiffuse(0.75)
    pr.SetAmbient(0.25)
    return a


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


def digit_actor(ch, x, y, z, height=17.0, color=(1.0, 0.52, 0.12), opacity=1.0, lit=True):
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
    p.SetColor(*color)
    p.SetOpacity(opacity)
    if lit:
        p.SetAmbient(1.0)
        p.SetDiffuse(0.0)
    else:
        p.SetAmbient(0.3)
        p.SetDiffuse(0.6)
    return a


STACK = "1234567890"   # IN-14 cathode stack, front to back (order illustrative)


def nixie_digits(digits, z_chassis=0.0):
    """Lit numeral with a soft halo, and the unlit cathodes faintly visible behind it, for each tube."""
    acts = []
    zdig = B.PCB_TOP_Z + B.SPACER_H + 24 + z_chassis
    for ch, (x, y) in zip(digits, B.TUBES):
        if not ch.strip():
            continue
        acts.append(digit_actor(ch, x, y - 4.0, zdig, color=(1.0, 0.78, 0.42)))                     # the lit cathode
        acts.append(digit_actor(ch, x, y - 3.4, zdig, height=18.8, color=(1.0, 0.42, 0.06), opacity=0.55))  # glow halo
        for k, c in enumerate(c for c in STACK if c != ch):                                          # unlit cathodes behind
            acts.append(digit_actor(c, x, y - 2.4 + k * 0.7, zdig, color=(0.45, 0.38, 0.33), opacity=0.13, lit=False))
    return acts


def screw_heads(z=0.0, y=0.0):
    """Domed brass heads of the six bezel screws (render only; the screws are bought parts)."""
    acts = []
    for x, zz in B.BEZEL_SCREWS:
        head = B.cq.Workplane("XZ").sphere(1.9).intersect(B.cq.Workplane("XZ").rect(5, 5).extrude(5)).translate((x, B.WY0 - B.BEZEL_T + y, zz + z))
        acts.append(brass_actor(head))
    return acts


def render(actors, path, cam_pos, focal, size=(1600, 900), view_angle=24, caption=None, glow_lights=None, ground=True):
    r = vtk.vtkRenderer()
    r.GradientBackgroundOn()
    r.SetBackground(0.035, 0.03, 0.028)
    r.SetBackground2(0.16, 0.13, 0.11)
    r.SetUseDepthPeeling(int(PEEL))
    r.SetOcclusionRatio(0.0)
    for a in actors:
        r.AddActor(a)
    if ground:   # dark table top under the feet
        plane = vtk.vtkPlaneSource()
        plane.SetOrigin(-330, -330, -B.FOOT_H - 0.05)
        plane.SetPoint1(560, -330, -B.FOOT_H - 0.05)
        plane.SetPoint2(-330, 420, -B.FOOT_H - 0.05)
        pm = vtk.vtkPolyDataMapper()
        pm.SetInputConnection(plane.GetOutputPort())
        pa = vtk.vtkActor()
        pa.SetMapper(pm)
        pa.GetProperty().SetColor(0.09, 0.075, 0.065)
        pa.GetProperty().SetSpecular(0.35)
        pa.GetProperty().SetSpecularPower(8)
        r.AddActor(pa)
    lights = [((-260, -380, 420), 0.95, (1.0, 0.96, 0.9)), ((520, -160, 160), 0.35, (0.85, 0.9, 1.0)), ((117, 420, 300), 0.45, (1.0, 0.9, 0.8))]
    for pos, inten, col in lights:
        L = vtk.vtkLight()
        L.SetPosition(*pos)
        L.SetFocalPoint(*focal)
        L.SetIntensity(inten)
        L.SetColor(*col)
        L.SetLightTypeToSceneLight()
        r.AddLight(L)
    for x, y, z in (glow_lights or []):   # warm light from each lit tube
        L = vtk.vtkLight()
        L.SetPositional(True)
        L.SetPosition(x, y - 4, z)
        L.SetFocalPoint(x, y - 60, z)
        L.SetConeAngle(80)
        L.SetAttenuationValues(0.2, 0.012, 0.0)
        L.SetColor(1.0, 0.5, 0.15)
        L.SetIntensity(0.9)
        L.SetLightTypeToSceneLight()
        r.AddLight(L)
    cam = r.GetActiveCamera()
    cam.SetPosition(*cam_pos)
    cam.SetFocalPoint(*focal)
    cam.SetViewUp(0, 0, 1)
    cam.SetViewAngle(view_angle)
    r.ResetCameraClippingRange()
    near, far = cam.GetClippingRange()
    cam.SetClippingRange(max(near, 0.25 * math.dist(cam_pos, focal)), far)   # keep depth precision for 1 mm brass on wood
    if caption:
        txt = vtk.vtkTextActor()
        txt.SetInput(caption)
        tp = txt.GetTextProperty()
        tp.SetFontSize(22)
        tp.SetColor(0.96, 0.91, 0.86)
        txt.SetDisplayPosition(26, size[1] - 44)
        r.AddViewProp(txt)
        note = vtk.vtkTextActor()
        note.SetInput("CadQuery model render - not a photo of a built clock")
        note.GetTextProperty().SetFontSize(14)
        note.GetTextProperty().SetColor(0.54, 0.48, 0.42)
        note.SetDisplayPosition(26, 16)
        r.AddViewProp(note)
    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetAlphaBitPlanes(1)
    rw.SetMultiSamples(8)
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


WOOD_MAP = {   # board: (grain axis, cross axis, texture origin, texture seed)
    "08_wood_front": ("x", "z", (B.WX0, 0, -2), 7),
    "09_wood_back": ("x", "z", (B.WX0, 0, -3), 8),
    "10_wood_end_left": ("y", "z", (0, B.WY0 - 140, -2), 7),
    "11_wood_end_right": ("y", "z", (0, B.WY0 - 150, -3), 8),
    "12_wood_top": ("x", "y", (B.WX0, B.WY0 - 10, 0), 9),
}


def wood_actors(dz=0.0, spread=0.0):
    """The five boards; spread > 0 pulls them apart along their outward normals (woodwork view)."""
    out = {"08_wood_front": (0, -1, 0), "09_wood_back": (0, 1, 0), "10_wood_end_left": (-1, 0, 0),
           "11_wood_end_right": (1, 0, 0), "12_wood_top": (0, 0, 1)}
    acts = []
    for n, (au, av, o, seed) in WOOD_MAP.items():
        d = out[n]
        shp = B.PARTS[n][0]().translate((d[0] * spread, d[1] * spread, d[2] * spread + dz))
        oo = (o[0] + d[0] * spread, o[1] + d[1] * spread, o[2] + d[2] * spread + dz)
        acts.append(wood_actor(shp, au, av, oo, seed))
    return acts


def tube_glow(digits, z_chassis=0.0):
    zdig = B.PCB_TOP_Z + B.SPACER_H + 24 + z_chassis
    return [(x, y, zdig) for (x, y), ch in zip(B.TUBES, digits) if ch.strip()]


def scene(env, digits="100842", panel_opacity=0.28, z_chassis=0.0, z_inner=0.0, z_wood=0.0, z_rods=0.0, y_panel=0.0, y_bezel=0.0,
          z_feet=0.0, inner=True, wood=True, panel=True, rods=True, feet=True):
    mv = lambda shp, z: shp.translate((0, 0, z)) if z else shp
    acts = []
    for k, v in env.items():
        col, op, em, spec = {"PCB": ((0.035, 0.035, 0.04), 1, False, 0.35), "glass": ((1.0, 0.8, 0.6), 0.16, False, 0.9),
                             "spacer": ((0.1, 0.1, 0.1), 1, False, 0.15), "lamp": ((1.0, 0.45, 0.1), 0.95, True, 0.15),
                             "button": ((0.35, 0.35, 0.36), 1, False, 0.15)}[k.split("_")[0]]
        acts.append(actor_from_shape(mv(v, z_chassis), col, op, specular=spec, emissive=em))
    acts.append(actor_from_shape(mv(B.bottom_cover(), z_chassis), (0.2, 0.2, 0.21)))
    acts.append(actor_from_shape(mv(B.cable_clamp(), z_chassis), (0.2, 0.2, 0.21)))
    acts += nixie_digits(digits, z_chassis)
    for x, y in (B.BUTTONS.values() if rods else []):
        acts.append(brass_actor(mv(B.button_rod(x, y), z_rods)))
    if inner:
        acts.append(actor_from_shape(mv(B.case_shell(), z_inner), (0.07, 0.07, 0.075), specular=0.05))
    if wood:
        acts += wood_actors(z_wood)
        acts.append(brass_actor(B.brass_bezel().translate((0, y_bezel, z_wood))))
        acts += screw_heads(z_wood, y_bezel)
    if feet:
        for x, y in B.CASE_SCREWS:
            acts.append(brass_actor(mv(B.brass_foot(x, y), z_feet)))
    if panel:
        acts.append(actor_from_shape(B.window_panel().translate((0, y_panel, 0)), (0.26, 0.2, 0.16), panel_opacity, specular=1.0))
    return acts


def main():
    env = B.pcb_mechanical()
    for old in ("hero_all_printed.png", "hero_clear_top.png", "hood_underside.png", "frame_from_above.png", "part_02_bottom_cover.png",
                "hero_alarm_clock.png", "part_14_brass_foot.png"):
        (OUT / old).unlink(missing_ok=True)
    glow = tube_glow("100842")
    render(scene(env), OUT / "hero_heirloom.png", (117 + 190, -420, 230), (117, 40, 58), view_angle=27, glow_lights=glow,
           caption="Rev C heirloom case: walnut, brass and six IN-14 tubes (model)")
    render(scene(env, panel_opacity=0.24), OUT / "hero_front.png", (117, -520, 66), (117, 40, 58), view_angle=24, glow_lights=glow,
           caption="Front view (model)")
    render(scene(env, digits="235959"), OUT / "hero_side.png", (-330, -330, 170), (117, 40, 52), view_angle=27, glow_lights=tube_glow("235959"),
           caption="From the left: mitred corners, brass feet and buttons (model)")
    render(scene(env, inner=False, wood=False, panel=False, rods=False, feet=False), OUT / "chassis.png", (117 + 160, -330, 220), (117, 40, 35),
           view_angle=27, caption="Chassis: floor + PCB + tubes, case removed (model)", glow_lights=glow, ground=False)
    render(scene(env, wood=False, feet=False), OUT / "printed_edition.png", (117 + 190, -420, 230), (117, 40, 56), view_angle=27, glow_lights=glow,
           caption="Printed inner case on its own: the printed edition and the fit test before woodwork (model)")
    shell = actor_from_shape(B.case_shell().rotate((117, 40, 56), (118, 40, 56), 180), (0.6, 0.6, 0.63))
    render([shell], OUT / "case_underside.png", (117 - 60, -170, 560), (140, 40, 50), ground=False, view_angle=30,
           caption="01 inner case from below: window slot rails, button guides, light baffle, corner blocks")
    render(wood_actors(spread=55) + [brass_actor(B.brass_bezel().translate((0, -110, 0)))], OUT / "woodwork.png",
           (117 + 420, -560, 420), (117, 40, 60), size=(1600, 1000), view_angle=30, ground=False,
           caption="Woodwork: five 9.5 mm boards, 45-degree mitres, brass bezel (model)")
    for name in ("02_floor", "03_cable_clamp", "04_button_rod", "06_fit_coupon", "07_unpowered_lead_pattern_coupon"):
        fn, flip, _ = B.PARTS[name]
        s = B.print_orient(fn(), flip)
        bb = s.val().BoundingBox()
        c = ((bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2, bb.zmax / 2)
        d = max(bb.xlen, bb.ylen, bb.zlen) * 1.9
        render([actor_from_shape(s, (0.85, 0.52, 0.22), specular=0.2)], OUT / f"part_{name}.png",
               (c[0] + d * 0.45, c[1] - d, c[2] + d * 0.8), c, size=(900, 560), caption=f"{name} (print orientation)", ground=False)
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
    """Exploded view, numbered in assembly order."""
    z_inner, z_wood, z_rods, y_panel, y_bezel, z_feet = 140, 290, 330, -170, -70, -70
    acts = scene(env, z_inner=z_inner, z_wood=z_wood, z_rods=z_rods, y_panel=y_panel, y_bezel=y_bezel, z_feet=z_feet, panel_opacity=0.6)
    xl = B.WX1 + 14
    acts += [label3d("1  walnut box (5 mitred boards) + brass bezel", (xl, 40, z_wood + 60)),
             label3d("2  inner case: 4x M2x8 up into the wood top", (xl, 40, z_inner + 60)),
             label3d("3  smoked window slides up into the inner case", (B.PANEL_X0 - 40, y_panel, -34)),
             label3d("4  chassis: floor + PCB + tubes (5x M2x6)", (xl, 40, 12)),
             label3d("5  button rods drop in from the top", (xl, 40, z_rods + 80)),
             label3d("6  brass feet: 4x M2x16 up into the case", (xl, 40, z_feet - 4))]
    render(acts, OUT / "exploded.png", (117 + 560, -900, 560), (180, 0, 190), size=(1600, 1350), view_angle=31, ground=False,
           caption="Exploded view: numbers show the assembly order (model)", glow_lights=tube_glow("100842"))


if __name__ == "__main__":
    main()
