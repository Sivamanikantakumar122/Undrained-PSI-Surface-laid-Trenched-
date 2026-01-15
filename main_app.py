import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Import your existing backend classes
# Ensure these files are in the same directory
from psi_backend import PSI_Undrained_Model
from trenched_psi_backend import Trenched_PSI_Backend

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Unified PSI Analysis Tool", layout="wide")
st.title("Unified Pipe-Soil Interaction Analysis")
st.markdown("### DNV-RP-F114 Compliance Model")

# --- MASTER SELECTOR ---
st.sidebar.title("Analysis Configuration")
analysis_mode = st.sidebar.radio(
    "Select Analysis Mode:",
    ["Surface Laid Pipeline", "Trenched Pipeline"],
    index=0
)

st.sidebar.markdown("---")

# =========================================================
# MODE 1: SURFACE LAID ANALYSIS
# =========================================================
if analysis_mode == "Surface Laid Pipeline":
    st.subheader("Surface Laid Analysis (Undrained)")
    st.markdown("Calculates Vertical, Axial, and Lateral resistance for exposed pipes.")
    
    # --- INPUTS (From psi_app.py) ---
    st.sidebar.header("1. Surface Laid Geometry")
    col1, col2 = st.sidebar.columns(2)
    with col1:
        # Cited from psi_app.py [cite: 1]
        Dop = st.number_input("Outer Diameter (Dop) [m]", value=0.40, format="%.3f")
        tp = st.number_input("Wall Thickness (tp) [m]", value=0.015, format="%.3f")
        Z = st.number_input("Embedment Depth (Z) [m]", value=0.10, format="%.3f")
    with col2:
        # Cited from psi_app.py [cite: 1-2]
        Su = st.number_input("Shear Strength (Su) [kPa]", value=5.0, format="%.2f")
        OCR = st.number_input("OCR", value=1.0, format="%.2f")
        St = st.number_input("Sensitivity (St)", value=3.0, format="%.2f")

    st.sidebar.header("2. Interaction Factors")
    # Cited from psi_app.py [cite: 2]
    alpha = st.sidebar.number_input("Adhesion Factor (alpha)", value=1.0, format="%.2f")
    rate = st.sidebar.number_input("Displacement Rate", value=1.0, format="%.2f")
    sub_wt_input = st.sidebar.number_input("Submerged Wt Input (from B9)", value=18.0)

    with st.sidebar.expander("Advanced Coefficients (SSR & Prem)"):
        # Cited from psi_app.py [cite: 3-4]
        st.markdown("**Concrete Surface**")
        c_ssr = [
            st.number_input("Conc SSR (Low)", value=0.25),
            st.number_input("Conc SSR (Best)", value=0.25),
            st.number_input("Conc SSR (High)", value=0.25)
        ]
        c_prem = [
            st.number_input("Conc Prem (Low)", value=0.2),
            st.number_input("Conc Prem (Best)", value=0.25),
            st.number_input("Conc Prem (High)", value=0.3)
        ]
        
        st.markdown("**PET Surface**")
        p_ssr = [
            st.number_input("PET SSR (Low)", value=0.25),
            st.number_input("PET SSR (Best)", value=0.25),
            st.number_input("PET SSR (High)", value=0.25)
        ]
        p_prem = [
            st.number_input("PET Prem (Low)", value=0.15),
            st.number_input("PET Prem (Best)", value=0.2),
            st.number_input("PET Prem (High)", value=0.25)
        ]

    # --- EXECUTION ---
    if st.button("Run Surface Analysis", type="primary"):
        # Initialize Backend [cite: 5, 16]
        model = PSI_Undrained_Model(
            Dop, tp, Z, Su, OCR, St, alpha, rate, sub_wt_input,
            c_ssr, c_prem, p_ssr, p_prem
        )
        
        weights, geo, df_results = model.run_simulation()
        
        # --- OUTPUTS ---
        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        # Cited from psi_app.py [cite: 6]
        c1.metric("Pipe Weight (Wp)", f"{weights['Wp']:.2f} kg/m")
        c2.metric("Flooded Wt (Wpf)", f"{weights['Wpf']:.2f} kN/m")
        c3.metric("Effective Force (V)", f"{weights['V']:.2f} kN/m")
        c4.metric("Wedging (zeta)", f"{geo['zeta']:.3f}")
        
        c5, c6 = st.columns(2)
        c5.metric("Penetration Area", f"{geo['Abm']:.4f} m²")
        
        # Logic for V vs Qv warning [cite: 7]
        delta_v_qv = weights['V'] - geo['Qv']
        c6.metric("Soil Resistance (Qv)", f"{geo['Qv']:.2f} kN/m", delta=f"{delta_v_qv:.2f} (V-Qv)", delta_color="inverse")
        
        if weights['V'] >= geo['Qv']:
            st.error(f"WARNING: V ({weights['V']:.2f}) >= Qv ({geo['Qv']:.2f}) - Pipe may sink.")
        else:
            st.success("Stability Check Passed: V < Qv")

        # Tables [cite: 8]
        st.markdown("#### Resistance Tables")
        tab1, tab2 = st.tabs(["Concrete Surface", "PET Surface"])
        with tab1:
            st.dataframe(df_results[df_results["Surface"] == "Concrete"].drop(columns=["Surface"]), use_container_width=True)
        with tab2:
            st.dataframe(df_results[df_results["Surface"] == "PET"].drop(columns=["Surface"]), use_container_width=True)

        # Plotting [cite: 9-10]
        st.subheader("Force-Displacement Curves")
        plot_surface = st.selectbox("Select Surface to Plot", ["Concrete", "PET"])
        subset = df_results[df_results["Surface"] == plot_surface]
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        for index, row in subset.iterrows():
            x_pts = [0, row['Xbrk (mm)'], row['Xres (mm)']]
            y_pts = [0, row['Axial Brk (kN/m)'], row['Axial Res (kN/m)']]
            ax1.plot(x_pts, y_pts, marker='o', label=row['Estimate'])
        
        ax1.set_title(f"{plot_surface} - Axial")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        for index, row in subset.iterrows():
            x_pts = [0, row['Ybrk (mm)'], row['Yres (mm)']]
            y_pts = [0, row['Lat Brk (kN/m)'], row['Lat Res (kN/m)']]
            ax2.plot(x_pts, y_pts, marker='o', label=row['Estimate'])

        ax2.set_title(f"{plot_surface} - Lateral")
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        st.pyplot(fig)

# =========================================================
# MODE 2: TRENCHED ANALYSIS
# =========================================================
elif analysis_mode == "Trenched Pipeline":
    st.subheader("Trenched Pipeline Analysis")
    st.markdown("Calculates Axial and Uplift resistance for buried pipes.")
    
    # --- INPUTS (From trenched_psi_app.py) ---
    st.sidebar.header("1. Trenched Geometry")
    # Cited from trenched_psi_app.py [cite: 11]
    dop = st.sidebar.number_input("Outer Diameter (Dop) [m]", value=0.40, format="%.3f", key="t_dop")
    tp = st.sidebar.number_input("Wall Thickness (tp) [m]", value=0.015, format="%.3f", key="t_tp")
    h_trench = st.sidebar.number_input("Trench Height (H) [m]", value=1.00, format="%.2f", key="t_h")

    st.subheader("2. Soil Parameters (P5 / P50 / P95)")
    col1, col2, col3 = st.columns(3)

    # Cited from trenched_psi_app.py [cite: 12-13]
    with col1:
        st.markdown("### P5 (Low)")
        alpha_p5 = st.number_input("Alpha", value=0.5, key="a_p5")
        gbulk_p5 = st.number_input("Gamma Bulk", value=16.0, key="g_p5")
        sbnb_p5 = st.number_input("Su Backfill Non-Brittle", value=2.0, key="sbnb_p5")
        sbo_p5 = st.number_input("Su Breakout", value=3.0, key="sbo_p5")
        sba_p5 = st.number_input("Su Backfill Axial", value=2.5, key="sba_p5")

    with col2:
        st.markdown("### P50 (Best)")
        alpha_p50 = st.number_input("Alpha", value=0.6, key="a_p50")
        gbulk_p50 = st.number_input("Gamma Bulk", value=17.0, key="g_p50")
        sbnb_p50 = st.number_input("Su Backfill Non-Brittle", value=3.0, key="sbnb_p50")
        sbo_p50 = st.number_input("Su Breakout", value=4.0, key="sbo_p50")
        sba_p50 = st.number_input("Su Backfill Axial", value=3.5, key="sba_p50")

    with col3:
        st.markdown("### P95 (High)")
        alpha_p95 = st.number_input("Alpha", value=0.8, key="a_p95")
        gbulk_p95 = st.number_input("Gamma Bulk", value=18.0, key="g_p95")
        sbnb_p95 = st.number_input("Su Backfill Non-Brittle", value=5.0, key="sbnb_p95")
        sbo_p95 = st.number_input("Su Breakout", value=6.0, key="sbo_p95")
        sba_p95 = st.number_input("Su Backfill Axial", value=5.0, key="sba_p95")

    # Consolidate inputs [cite: 14]
    soil_inputs = {
        'alpha': [alpha_p5, alpha_p50, alpha_p95],
        'g_bulk': [gbulk_p5, gbulk_p50, gbulk_p95],
        's_bnb': [sbnb_p5, sbnb_p50, sbnb_p95],
        's_bo': [sbo_p5, sbo_p50, sbo_p95],
        's_ba': [sba_p5, sba_p50, sba_p95]
    }

    # --- EXECUTION ---
    if st.button("Run Trenched Analysis", type="primary"):
        # Initialize Backend [cite: 14, 41]
        model = Trenched_PSI_Backend(dop, tp, h_trench)
        
        v_eff, df_results = model.run_analysis(soil_inputs)
        
        # --- OUTPUTS ---
        st.divider()
        st.metric("Effective Vertical Force (V)", f"{v_eff:.2f} kN/m")
        
        # Display Table [cite: 15]
        df_display = df_results.set_index("Category").T
        st.table(df_display)
        
        # Chart
        st.subheader("Resistance Comparison")
        st.bar_chart(df_results.set_index("Category"))
