"""Interactive 3D Beam Deflection Simulator

Run with:
    pip install -r requirements_beam_simulator.txt
    streamlit run beam_deflection_simulator.py

Educational model: Euler-Bernoulli beam theory, linear elastic material,
small deflections, constant cross-section, and downward loads.
"""

import numpy as np
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="3D Beam Deflection Simulator",
    page_icon="📐",
    layout="wide",
)

st.title("3D Beam Deflection Simulator")
st.caption(
    "Strength of Materials • Beam deflection under point loads, UDL, UVL, and combined loading"
)

st.markdown(
    """
    Change the beam, material, support, and load parameters in the sidebar. The plots and
    calculated results update automatically. The 3D deflection is magnified for visibility;
    the numerical results always use the actual calculated deflection.
    """
)


# ------------------------------ Sidebar inputs ------------------------------
st.sidebar.header("1. Beam and support")
span_m = st.sidebar.slider("Beam span, L (m)", min_value=1.0, max_value=10.0, value=4.0, step=0.5)
support = st.sidebar.selectbox("Support condition", ["Simply supported", "Cantilever"])

st.sidebar.header("2. Material")
modulus_defaults = {"Structural steel": 200.0, "Aluminium": 69.0, "Custom": 200.0}


def reset_modulus_for_material() -> None:
    """Update the suggested modulus when the material selection changes."""
    selected_material = st.session_state.get("material", "Structural steel")
    st.session_state["modulus_gpa"] = modulus_defaults[selected_material]


material = st.sidebar.selectbox(
    "Material",
    ["Structural steel", "Aluminium", "Custom"],
    key="material",
    on_change=reset_modulus_for_material,
)
modulus_gpa = st.sidebar.number_input(
    "Young's modulus, E (GPa)",
    min_value=1.0,
    max_value=1000.0,
    value=modulus_defaults[material],
    key="modulus_gpa",
    step=1.0,
    help="Typical values: steel ≈ 200 GPa; aluminium ≈ 69 GPa. You can edit this value for any material.",
)

st.sidebar.header("3. Cross-section")
section_shape = st.sidebar.selectbox("Cross-section shape", ["Rectangular", "Circular"])
if section_shape == "Rectangular":
    width_mm = st.sidebar.number_input("Width, b (mm)", min_value=5.0, max_value=500.0, value=50.0, step=5.0)
    depth_mm = st.sidebar.number_input(
        "Vertical depth, h (mm)", min_value=5.0, max_value=500.0, value=100.0, step=5.0,
        help="The vertical depth is cubed in I = b h³ / 12, so it strongly affects deflection.",
    )
    width_m = width_mm / 1000.0
    depth_m = depth_mm / 1000.0
    second_moment = width_m * depth_m**3 / 12.0
    outer_fibre_m = depth_m / 2.0
    section_text = f"Rectangular ({width_mm:g} mm × {depth_mm:g} mm)"
else:
    diameter_mm = st.sidebar.number_input("Diameter, d (mm)", min_value=5.0, max_value=500.0, value=50.0, step=5.0)
    diameter_m = diameter_mm / 1000.0
    second_moment = np.pi * diameter_m**4 / 64.0
    outer_fibre_m = diameter_m / 2.0
    section_text = f"Circular (diameter {diameter_mm:g} mm)"

st.sidebar.header("4. Loading")
load_case = st.sidebar.selectbox(
    "Load case",
    ["Point load", "Uniformly distributed load (UDL)", "Uniformly varying load (UVL)", "Multiple loads"],
)

point_loads = []  # each entry is (force in N, position in m)
load_description = ""

if load_case == "Point load":
    load_kn = st.sidebar.number_input("Point load, P (kN, downward)", min_value=0.0, max_value=1000.0, value=5.0, step=0.5)
    pos_pct = st.sidebar.slider("Point-load position (% of span from left end)", 0, 100, 50, 5)
    point_loads.append((load_kn * 1000.0, span_m * pos_pct / 100.0))
    load_description = f"Point load: {load_kn:g} kN at {pos_pct}% of span"

elif load_case == "Uniformly distributed load (UDL)":
    udl_kn_m = st.sidebar.number_input("Uniform load, w (kN/m, downward)", min_value=0.0, max_value=1000.0, value=2.0, step=0.5)
    load_description = f"UDL: {udl_kn_m:g} kN/m over the full span"

elif load_case == "Uniformly varying load (UVL)":
    uvl_max_kn_m = st.sidebar.number_input(
        "Maximum load intensity, wₘₐₓ (kN/m)", min_value=0.0, max_value=1000.0, value=3.0, step=0.5,
        help="The triangular load increases linearly from zero at the left end to this value at the right end.",
    )
    load_description = f"Triangular UVL: 0 to {uvl_max_kn_m:g} kN/m from left to right"

else:
    st.sidebar.caption("Combined case: two point loads plus a uniform load over the full span.")
    p1_kn = st.sidebar.number_input("Point load 1, P₁ (kN)", min_value=0.0, max_value=1000.0, value=3.0, step=0.5)
    p1_pct = st.sidebar.slider("Position of P₁ (% of span)", 0, 100, 30, 5)
    p2_kn = st.sidebar.number_input("Point load 2, P₂ (kN)", min_value=0.0, max_value=1000.0, value=2.0, step=0.5)
    p2_pct = st.sidebar.slider("Position of P₂ (% of span)", 0, 100, 70, 5)
    udl_kn_m = st.sidebar.number_input("Uniform load, w (kN/m)", min_value=0.0, max_value=1000.0, value=1.0, step=0.5)
    point_loads.append((p1_kn * 1000.0, span_m * p1_pct / 100.0))
    point_loads.append((p2_kn * 1000.0, span_m * p2_pct / 100.0))
    load_description = (
        f"P₁ = {p1_kn:g} kN at {p1_pct}%; P₂ = {p2_kn:g} kN at {p2_pct}%; "
        f"UDL = {udl_kn_m:g} kN/m"
    )

st.sidebar.header("5. Visualisation")
magnification = st.sidebar.slider("3D deformation magnification", min_value=1, max_value=100, value=25, step=1)


# ------------------------------ Beam analysis -------------------------------
# Units used internally:
#   length: m; force: N; distributed load: N/m; E: Pa; I: m^4; moment: N·m; deflection: m
E_pa = modulus_gpa * 1e9
N_NODES = 501
x = np.linspace(0.0, span_m, N_NODES)
dx = x[1] - x[0]
x_mid = (x[:-1] + x[1:]) / 2.0

# Distributed load intensity evaluated at cell midpoints (N/m), positive downward.
q_mid = np.zeros_like(x_mid)
if load_case == "Uniformly distributed load (UDL)":
    q_mid[:] = udl_kn_m * 1000.0
elif load_case == "Uniformly varying load (UVL)":
    q_mid = (uvl_max_kn_m * 1000.0) * x_mid / span_m
elif load_case == "Multiple loads":
    q_mid[:] = udl_kn_m * 1000.0

# Treat each small distributed-load cell as a point force at its midpoint for numerical integration.
dist_forces_n = q_mid * dx

if support == "Simply supported":
    total_moment_about_right = 0.0
    for force_n, position_m in point_loads:
        total_moment_about_right += force_n * (span_m - position_m)
    total_moment_about_right += np.sum(dist_forces_n * (span_m - x_mid))
    reaction_left_n = total_moment_about_right / span_m

    bending_moment = reaction_left_n * x
    for force_n, position_m in point_loads:
        bending_moment -= force_n * np.maximum(x - position_m, 0.0)
    # Distributed-load contribution to M(x).
    bending_moment -= np.sum(
        dist_forces_n[None, :] * np.maximum(x[:, None] - x_mid[None, :], 0.0), axis=1
    )
    # Negative moment is used here for downward deflection.
    bending_moment = -bending_moment
else:
    # Cantilever fixed at x = 0; internal moment at each section is due to loads to its right.
    bending_moment = np.zeros_like(x)
    for force_n, position_m in point_loads:
        bending_moment -= force_n * np.maximum(position_m - x, 0.0)
    bending_moment -= np.sum(
        dist_forces_n[None, :] * np.maximum(x_mid[None, :] - x[:, None], 0.0), axis=1
    )
    reaction_left_n = sum(force for force, _ in point_loads) + np.sum(dist_forces_n)

# Euler-Bernoulli beam relation: E I v''(x) = M(x).
curvature = bending_moment / (E_pa * second_moment)


def cumulative_trapezoid(y_values: np.ndarray, x_values: np.ndarray) -> np.ndarray:
    """Cumulative trapezoidal integration with initial value zero (NumPy-only)."""
    increments = (y_values[:-1] + y_values[1:]) * 0.5 * np.diff(x_values)
    return np.concatenate(([0.0], np.cumsum(increments)))


slope_from_curvature = cumulative_trapezoid(curvature, x)
deflection_base = cumulative_trapezoid(slope_from_curvature, x)
if support == "Simply supported":
    # Enforce v(0) = v(L) = 0 by solving for the unknown initial slope.
    initial_slope = -deflection_base[-1] / span_m
else:
    # Cantilever: v(0) = 0 and v'(0) = 0.
    initial_slope = 0.0

deflection_m = deflection_base + initial_slope * x

max_deflection_index = int(np.argmax(np.abs(deflection_m)))
max_deflection_m = float(np.abs(deflection_m[max_deflection_index]))
max_deflection_mm = max_deflection_m * 1000.0
max_deflection_position_m = float(x[max_deflection_index])
max_moment_nm = float(np.max(np.abs(bending_moment)))
max_moment_knm = max_moment_nm / 1000.0
max_bending_stress_pa = max_moment_nm * outer_fibre_m / second_moment if second_moment > 0 else 0.0
max_bending_stress_mpa = max_bending_stress_pa / 1e6


# --------------------------------- Results -----------------------------------
st.info(
    "Model assumptions: homogeneous, linearly elastic material; small deflection; constant E and I; "
    "Euler–Bernoulli beam theory; downward loading only. UVL is triangular and increases from left to right."
)

metric_cols = st.columns(4)
metric_cols[0].metric("Maximum deflection", f"{max_deflection_mm:.3f} mm")
metric_cols[1].metric("Location of maximum", f"x = {max_deflection_position_m:.3f} m")
metric_cols[2].metric("Maximum bending moment", f"{max_moment_knm:.3f} kN·m")
metric_cols[3].metric("Maximum bending stress", f"{max_bending_stress_mpa:.2f} MPa")


# ---------------------------------- Plots ------------------------------------
col_3d, col_2d = st.columns([1.2, 1])

with col_3d:
    st.subheader("Interactive 3D view")
    z_deformed = deflection_m * magnification
    fig3d = go.Figure()
    fig3d.add_trace(
        go.Scatter3d(
            x=x, y=np.zeros_like(x), z=np.zeros_like(x),
            mode="lines", name="Original beam",
            line=dict(color="#64748b", width=7, dash="dash"),
            hovertemplate="x = %{x:.3f} m<br>Original position<extra></extra>",
        )
    )
    fig3d.add_trace(
        go.Scatter3d(
            x=x, y=np.zeros_like(x), z=z_deformed,
            mode="lines", name="Deformed beam (magnified)",
            line=dict(color="#e45756", width=8),
            customdata=np.column_stack((deflection_m * 1000.0, bending_moment / 1000.0)),
            hovertemplate=("x = %{x:.3f} m<br>Deflection = %{customdata[0]:.4f} mm"
                           "<br>Bending moment = %{customdata[1]:.4f} kN·m<extra></extra>"),
        )
    )

    # Draw simple downward load arrows in the 3D view.
    arrow_x = []
    arrow_y = []
    arrow_z = []
    arrow_text_x = []
    arrow_text = []
    arrow_height = max(span_m * 0.055, max_deflection_m * magnification * 0.5, 0.08)
    for force_n, position_m in point_loads:
        arrow_x.extend([position_m, position_m, None])
        arrow_y.extend([0.0, 0.0, None])
        arrow_z.extend([arrow_height, 0.0, None])
        arrow_text_x.append(position_m)
        arrow_text.append(f"{force_n / 1000.0:g} kN")
    if load_case in ("Uniformly distributed load (UDL)", "Multiple loads") and np.max(q_mid) > 0:
        for position_m in np.linspace(0.08 * span_m, 0.92 * span_m, 11):
            arrow_x.extend([position_m, position_m, None])
            arrow_y.extend([0.0, 0.0, None])
            arrow_z.extend([arrow_height * 0.8, 0.0, None])
    elif load_case == "Uniformly varying load (UVL)" and np.max(q_mid) > 0:
        for position_m in np.linspace(0.12 * span_m, 0.92 * span_m, 9):
            height = arrow_height * (position_m / span_m)
            arrow_x.extend([position_m, position_m, None])
            arrow_y.extend([0.0, 0.0, None])
            arrow_z.extend([height, 0.0, None])

    if arrow_x:
        fig3d.add_trace(
            go.Scatter3d(
                x=arrow_x, y=arrow_y, z=arrow_z,
                mode="lines", name="Applied loads",
                line=dict(color="#2563eb", width=3),
                hoverinfo="skip",
            )
        )
    if arrow_text_x:
        fig3d.add_trace(
            go.Scatter3d(
                x=arrow_text_x, y=[0.0] * len(arrow_text_x), z=[arrow_height * 1.12] * len(arrow_text_x),
                mode="text", text=arrow_text, name="Point-load labels",
                textfont=dict(color="#2563eb", size=10), showlegend=False, hoverinfo="skip",
            )
        )

    # Simplified supports: small base marks at beam ends.
    support_z = -arrow_height * 0.12
    support_x_positions = [0.0, span_m] if support == "Simply supported" else [0.0]
    for support_x in support_x_positions:
        fig3d.add_trace(
            go.Scatter3d(
                x=[support_x, support_x], y=[-0.08, 0.08], z=[support_z, support_z],
                mode="lines", name="Support", line=dict(color="#0f766e", width=6),
                showlegend=(support_x == support_x_positions[0]), hoverinfo="skip",
            )
        )

    fig3d.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=25, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        scene=dict(
            xaxis_title="Span, x (m)",
            yaxis_title="Width direction (visual only)",
            zaxis_title="Vertical position (magnified)",
            aspectmode="manual",
            aspectratio=dict(x=1.8, y=0.25, z=0.75),
            camera=dict(eye=dict(x=1.5, y=1.6, z=1.15)),
        ),
    )
    st.plotly_chart(fig3d, use_container_width=True)
    st.caption(f"The deformed shape is displayed at {magnification}× magnification. Actual deflection: {max_deflection_mm:.3f} mm.")

with col_2d:
    st.subheader("Deflection curve")
    fig2d = go.Figure()
    fig2d.add_trace(
        go.Scatter(x=x, y=np.zeros_like(x), mode="lines", name="Original beam", line=dict(color="#64748b", dash="dash"))
    )
    fig2d.add_trace(
        go.Scatter(
            x=x, y=deflection_m * 1000.0, mode="lines", name="Deflected beam",
            line=dict(color="#e45756", width=3),
            hovertemplate="x = %{x:.3f} m<br>Deflection = %{y:.4f} mm<extra></extra>",
        )
    )
    fig2d.update_layout(
        height=520,
        margin=dict(l=15, r=15, t=25, b=15),
        xaxis_title="Position along beam, x (m)",
        yaxis_title="Vertical deflection (mm; downward is negative)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
    )
    fig2d.update_yaxes(zeroline=True, zerolinewidth=1)
    st.plotly_chart(fig2d, use_container_width=True)


# ---------------------------- Calculation summary ---------------------------
st.subheader("Calculation summary")
summary_col1, summary_col2 = st.columns(2)
with summary_col1:
    st.markdown(
        f"""
        **Selected configuration**

        - Support: {support}
        - Span: {span_m:.2f} m
        - Material: {material}
        - Young's modulus: {modulus_gpa:.1f} GPa
        - Cross-section: {section_text}
        - Second moment of area, I: {second_moment:.6e} m⁴
        - Loading: {load_description}
        """
    )
with summary_col2:
    st.markdown(
        """
        **Equations used**

        - Flexural rigidity: **EI**
        - Euler–Bernoulli equation: **EI · d²v/dx² = M(x)**
        - Rectangular section: **I = b h³ / 12**
        - Circular section: **I = π d⁴ / 64**
        - Maximum bending stress: **σₘₐₓ = Mₘₐₓ c / I**

        The moment curve is integrated numerically twice. Boundary conditions enforce zero
        deflection at both supports for a simply supported beam, or zero deflection and slope
        at the fixed end for a cantilever.
        """
    )

with st.expander("View numerical results"):
    import pandas as pd
    result_table = pd.DataFrame(
        {
            "Position x (m)": x,
            "Deflection (mm)": deflection_m * 1000.0,
            "Bending moment (kN·m)": bending_moment / 1000.0,
            "Bending stress at outer fibre (MPa)": (np.abs(bending_moment) * outer_fibre_m / second_moment) / 1e6,
        }
    )
    st.dataframe(result_table, use_container_width=True, hide_index=True)
    csv = result_table.to_csv(index=False).encode("utf-8")
    st.download_button("Download results as CSV", data=csv, file_name="beam_deflection_results.csv", mime="text/csv")

st.caption(
    "For coursework and demonstration only. Real beam design requires appropriate boundary conditions, "
    "load combinations, factors of safety, and code-compliant verification."
)
