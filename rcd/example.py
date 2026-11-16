"""Demonstration project. The robot is a FICTIONAL generic 6-axis robot: dimensions are illustrative inputs, not a real model."""
import json


def segment(name, shape, length, d1=None, **kw):
    s = dict(name=name, shape=shape, length=length, d1=d1, neutral_angle=0, cover=True)
    s.update(kw)
    return s


EXAMPLE = dict(
    name="DEMO — generic 6-axis robot (illustrative dimensions)",
    robot=dict(manufacturer="DEMO", model="Generic-6A (fictional)", version="n/a", type="articulated", axes=6, application="obróbka skrawaniem / machine tending",
               mounting="podłoga", segments=[
        segment("Base", "cylinder", 200, 300, joint_after=dict(type="twist", axis=1, min=-170, max=170),
                openings=[dict(name="Cable outlet", kind="round", pos_mm=100, angle_deg=90, size1=40, type="cable")]),
        segment("Shoulder", "cylinder", 260, 260, joint_after=dict(type="bend", axis=2, min=-60, max=60)),
        segment("Lower arm", "cylinder", 450, 160, neutral_angle=0, joint_after=dict(type="bend", axis=3, min=-45, max=45)),
        segment("Upper arm", "cylinder", 420, 130, neutral_angle=-90, joint_after=dict(type="twist", axis=4, min=-180, max=180)),
        segment("Wrist", "frustum", 150, 110, d2=80, joint_after=dict(type="none")),
    ]),
    environment=dict(tmin_c=10, tmax_c=40, tsurface_c=55, humidity_pct=70, cycles_per_day=6000, factors={
        "oil_cutting": dict(state="present", level=2), "emulsion": dict(state="present", level=2), "oil_hydraulic": dict(state="absent"),
        "metal_chips": dict(state="present", level=2), "dust_metal": dict(state="present", level=2), "abrasion": dict(state="present", level=2),
        "splash": dict(state="present", level=3), "sparks": dict(state="absent"), "spatter": dict(state="absent"), "uv": dict(state="absent"),
        "outdoor": dict(state="absent"), "acids": dict(state="absent"), "alkalis": dict(state="absent"), "solvents": dict(state="absent"),
        "fuels": dict(state="absent"), "detergents": dict(state="present", level=1), "disinfectants": dict(state="absent"),
        "steam": dict(state="absent"), "pressure_wash": dict(state="absent"), "water_jets": dict(state="absent"),
        "antistatic": dict(state="absent"), "esd": dict(state="absent"), "flame_retardant": dict(state="absent"),
        "waterproof": dict(state="present", level=1), "dust_tight": dict(state="absent"), "impact": dict(state="absent"),
        "hot_contact": dict(state="absent"), "radiant_heat": dict(state="absent"), "continuous_bending": dict(state="present", level=2),
        "contact_other": dict(state="absent")}),
    requirements=dict(scope="full", removable=True, modular=True, zipper=True, velcro=True, snaps=False, elastic=True, openings=True,
                      service_access=True, easy_clean=True, removal_per_month=4, lifetime_years=3, max_mass_kg=None, roll_width_mm=1500,
                      allow_rotate_90=False, layers=1, pleat_height_mm=20, material_override=None, confirmed={}),
)
