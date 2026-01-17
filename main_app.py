import streamlit as st
import pandas as pd

# --- IMPORT BACKENDS ---
try:
    import surfacelaid_psi_backend as surface_backend
    from trenched_psi_backend import Trenched_PSI_Backend
except ImportError as e:
    st.error(f"Error importing backend files: {e}. Please check your filenames in GitHub.")
    st.stop()

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Unified PSI Tool", layout="wide")
st.title("Unified Pipe-Soil Interaction Analysis")
st.markdown("### DNV-RP-F114 Compliance Model")
st.markdown("---")

# --- MASTER SELECTOR ---
st.sidebar.title("Analysis Mode")
analysis_mode = st.sidebar.radio(
    "Select Pipeline Condition:",
    ["Surface Laid Pipeline", "Trenched Pipeline"],
    index=0
)
st.sidebar.markdown("---")

# =========================================================
# MODE 1: SURFACE LAID ANALYSIS
# =========================================================
if analysis_mode == "Surface Laid Pipeline":
    st.subheader("Surface Laid Analysis (Undrained)")
    st.info("Calculates Vertical, Axial, and Lateral resistance profiles for exposed/partially embedded pipes.")

    # --- SIDEBAR INPUTS ---
    st.sidebar.header("1. Pipeline Geometry")
    Dop = st.sidebar.number_input("Outer Diameter (m)", value=0.3239, format="%.4f")
    tp = st.sidebar.number_input("Wall Thickness (m)", value=0.0127, format="%.4f")
    Z = st.sidebar.number_input("Embedment Depth Z (m)", value=0.05, format="%.3f")
    
    st.sidebar.header("2. Soil Properties")
    Su = st.sidebar.number_input("Shear Strength Su (kPa)", value=5.0)
    OCR = st.sidebar.number_input("OCR", value=1.0)
    St = st.sidebar.number_input("Sensitivity St", value=3.0)
    Su_passive = st.sidebar.number_input("Passive Su (kPa)", value=5.0)
    gamma_bulk = st.sidebar.number_input("Bulk Unit Weight (kN/m³)", value=16.0)
    
    st.sidebar.header("3. Interaction Factors")
    alpha = st.sidebar.number_input("Adhesion Factor α", value=0.5)
    rate = st.sidebar.number_input("Rate Factor", value=1.0)
    
    # Dynamic Input Generator for Surfaces
    def get_surface_params(surface_name):
        st.sidebar.subheader(f"{surface_name} Surface Settings")
        c1, c2 = st.sidebar.columns(2)
        p5_ssr = c1.number_input(f"{surface_name} P5 SSR", value=0.25)
        p5_prem = c2.number_input(f"{surface_name} P5 Prem", value=1.0)
        
        p50_ssr = c1.number_input(f"{surface_name} P50 SSR", value=0.35)
        p50_prem = c2.number_input(f"{surface_name} P50 Prem", value=1.0)
        
        p95_ssr = c1.number_input(f"{surface_name} P95 SSR", value=0.45)
        p95_prem = c2.number_input(f"{surface_name} P95 Prem", value=1.0)
        
        return {
            f"{surface_name}_P5_SSR": p5_ssr, f"{surface_name}_P5_Prem": p5_prem,
            f"{surface_name}_P50_SSR": p50_ssr, f"{surface_name}_P50_Prem": p50_prem,
            f"{surface_name}_P95_SSR": p95_ssr, f"{surface_name}_P95_Prem": p95_prem,
        }
        
    conc_data = get_surface_params("Concrete")
    pet_data = get_surface_params("PET")

    # --- EXECUTE ---
    if st.button("Run Surface Analysis", type="primary"):
        # Prepare inputs dictionary
        inputs = {
            'Dop': Dop, 'tp': tp, 'Z': Z, 'Su': Su, 'OCR': OCR, 'St': St,
            'alpha': alpha, 'rate': rate, 'gamma_bulk': gamma_bulk, 'Su_passive': Su_passive
        }
        inputs.update(conc_data)
        inputs.update(pet_data)

        # Call Backend
        results = surface_backend.run_psi_analysis(inputs)
        metrics = results["metrics"]

        # --- RESULTS ---
        st.divider()
        st.subheader("Calculation Summary")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Effective Force (V)", f"{metrics['V']:.3f} kN/m")
        col2.metric("Vertical Capacity (Qv)", f"{metrics['Qv']:.3f} kN/m")
        col3.metric("Wedging Factor (ζ)", f"{metrics['zeta']:.3f}")
        col4.metric("Lateral Passive Resist.", f"{metrics['Fl_remain']:.3f} kN/m")

        if metrics['V'] > metrics['Qv']:
            st.error("FAILURE WARNING: Effective Force (V) > Vertical Capacity (Qv). The pipe is likely to sink.")
        else:
            st.success("STABILITY OK: Effective Force (V) < Vertical Capacity (Qv).")

        # --- DATA TABLES ---
        st.subheader("Detailed Resistance Values")
        table_data = []
        for p in results["profiles"]:
            table_data.append({
                "Surface": p["Surface"],
                "Estimate": p["Estimate"],
                "Axial Brk (kN/m)": p["Axial"]["BreakForce"],
                "Xbrk (mm)": p["Axial"]["BreakDisp"],
                "Axial Res (kN/m)": p["Axial"]["ResForce"],
                "Xres (mm)": p["Axial"]["ResDisp"],
                "Lat Brk (kN/m)": p["Lateral"]["BreakForce"],
                "Ybrk (mm)": p["Lateral"]["BreakDisp"],
                "Lat Res (kN/m)": p["Lateral"]["ResForce"],
                "Yres (mm)": p["Lateral"]["ResDisp"]
            })
        
        df_results = pd.DataFrame(table_data)
        c1, c2 = st.tabs(["Concrete Table", "PET Table"])
        with c1:
            st.dataframe(df_results[df_results["Surface"] == "Concrete"].drop(columns=["Surface"]), use_container_width=True)
        with c2:
            st.dataframe(df_results[df_results["Surface"] == "PET"].drop(columns=["Surface"]), use_container_width=True)

# =========================================================
# MODE 2: TRENCHED ANALYSIS
# =========================================================
elif analysis_mode == "Trenched Pipeline":
    st.subheader("Trenched Pipeline Analysis")
    st.info("Calculates Axial and Uplift resistance for buried pipes.")

    # --- SIDEBAR INPUTS ---
    st.sidebar.header("1. Trenched Geometry")
    dop = st.sidebar.number_input("Outer Diameter (Dop) [m]", value=0.40, format="%.3f", key="t_dop")
    tp = st.sidebar.number_input("Wall Thickness (tp) [m]", value=0.015, format="%.3f", key="t_tp")
    h_trench = st.sidebar.number_input("Trench Height (H) [m]", value=1.00, format="%.2f", key="t_h")

    # Soil Inputs in Main Window
    st.subheader("2. Soil Parameters (P5 / P50 / P95)")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**P5 (Low)**")
        alpha_p5 = st.number_input("Alpha", value=0.5, key="a_p5")
        gbulk_p5 = st.number_input("Gamma Bulk", value=16.0, key="g_p5")
        sbnb_p5 = st.number_input("Su Backfill Non-Brittle", value=2.0, key="sbnb_p5")
        sbo_p5 = st.number_input("Su Breakout", value=3.0, key="sbo_p5")
        sba_p5 = st.number_input("Su Backfill Axial", value=2.5, key="sba_p5")

    with col2:
        st.markdown("**P50 (Best)**")
        alpha_p50 = st.number_input("Alpha", value=0.6, key="a_p50")
        gbulk_p50 = st.number_input("Gamma Bulk", value=17.0, key="g_p50")
        sbnb_p50 = st.number_input("Su Backfill Non-Brittle", value=3.0, key="sbnb_p50")
        sbo_p50 = st.number_input("Su Breakout", value=4.0, key="sbo_p50")
        sba_p50 = st.number_input("Su Backfill Axial", value=3.5, key="sba_p50")

    with col3:
        st.markdown("**P95 (High)**")
        alpha_p95 = st.number_input("Alpha", value=0.8, key="a_p95")
        gbulk_p95 = st.number_input("Gamma Bulk", value=18.0, key="g_p95")
        sbnb_p95 = st.number_input("Su Backfill Non-Brittle", value=5.0, key="sbnb_p95")
        sbo_p95 = st.number_input("Su Breakout", value=6.0, key="sbo_p95")
        sba_p95 = st.number_input("Su Backfill Axial", value=5.0, key="sba_p95")

    # Consolidate inputs
    soil_inputs = {
        'alpha': [alpha_p5, alpha_p50, alpha_p95],
        'g_bulk': [gbulk_p5, gbulk_p50, gbulk_p95],
        's_bnb': [sbnb_p5, sbnb_p50, sbnb_p95],
        's_bo': [sbo_p5, sbo_p50, sbo_p95],
        's_ba': [sba_p5, sba_p50, sba_p95]
    }

    # --- EXECUTE ---
    if st.button("Run Trenched Analysis", type="primary"):
        # Initialize Backend
        model = Trenched_PSI_Backend(dop, tp, h_trench)
        
        # Run Calculation
        v_eff, df_results = model.run_analysis(soil_inputs)
        
        # --- OUTPUTS ---
        st.divider()
        st.metric("Effective Vertical Force (V)", f"{v_eff:.2f} kN/m")
        
        # Display Table
        st.subheader("Resistance Summary")
        df_display = df_results.set_index("Category").T
        st.dataframe(df_display, use_container_width=True)

# --- FOOTER ---
st.markdown("---")
st.markdown("**Developed by Sivamanikanta Kumar** | Geotechnical Engineer")
