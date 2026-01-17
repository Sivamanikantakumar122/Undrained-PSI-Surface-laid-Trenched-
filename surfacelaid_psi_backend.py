import numpy as np

def run_psi_analysis(inputs):
    """
    Performs Undrained Pipe-Soil Interaction analysis.
    Calculates Axial and Lateral resistance profiles for given soil and pipe parameters.
    """
    # --- 1. EXTRACT INPUTS ---
    Dop = inputs['Dop']
    tp = inputs['tp']
    Z = inputs['Z']
    Su = inputs['Su']
    OCR = inputs['OCR']
    St = inputs['St']
    alpha = inputs['alpha']
    rate = inputs['rate']
    
    # Soil Weight correction (Bulk - 10.05 for Submerged)
    Sub_wt = inputs['gamma_bulk'] - 10.05 
    Su_passive = inputs['Su_passive'] 

    # --- 2. WEIGHT CALCULATIONS ---
    Dip = Dop - 2 * tp
    g = 9.8
    Klay = 2.0
    
    # Constants: 7850 (Steel), 1000 (Fluid), 1025 (Seawater)
    Wp = (np.pi * (Dop**2 - Dip**2) * 7850) / 4
    Wcon = (np.pi * Dip**2 * 1000) / 4
    Wb = (np.pi * Dop**2 * 1025) / 4
    
    Wpf = ((Wp + Wcon - Wb) * g) / 1000.0
    Wpins = (np.pi * (Dop**2 - Dip**2) * (7850 - 1025)) / 4
    
    # Effective Vertical Force V
    V = max((Wpins * Klay * g / 1000.0), Wpf)

    # --- 3. GEOMETRY & VERTICAL RESISTANCE (Qv) ---
    # Logic for Penetrated Area (Abm)
    if Z < Dop / 2:
        val = Dop * Z - Z**2
        B = 2 * np.sqrt(val) if val > 0 else 0
        if Dop > 0:
            asin_val = np.arcsin(B / Dop) if abs(B/Dop) <= 1 else 0
            Abm = (asin_val * (Dop**2 / 4)) - (B * (Dop / 4) * np.cos(asin_val))
        else:
            Abm = 0
    else:
        B = Dop
        Abm = (np.pi * Dop**2 / 8) + Dop * (Z - Dop / 2)
        
    # Vertical Bearing Capacity Qv
    if Dop > 0:
        term1 = 6 * (Z / Dop)**0.25
        term2 = 3.4 * (10 * Z / Dop)**0.5
        Qv = (min(term1, term2) + (1.5 * Sub_wt * Abm / (Dop * Su))) * Dop * Su
    else:
        Qv = 0

    # --- 4. WEDGING & LATERAL RESISTANCE ---
    # Wedging Factor (zeta)
    cosVal = 1 - Z / (Dop / 2)
    cosVal = max(-1.0, min(1.0, cosVal)) # Safety clamp
    beta = np.arccos(cosVal)
    
    denom = beta + np.sin(beta) * np.cos(beta)
    zeta = (2 * np.sin(beta)) / denom if denom != 0 else 1.0
    
    # Lateral Remaining Resistance (Passive Soil)
    Fl_remain = Z * rate * (2 * Su_passive + 0.5 * Sub_wt * Z)

    # --- 5. PREPARE RESULTS ---
    results = {
        "metrics": {
            "Wp": Wp, "Wpf": Wpf, "V": V, 
            "Abm": Abm, "Qv": Qv, "zeta": zeta, 
            "Fl_remain": Fl_remain, "Check_V_Qv": (V < Qv)
        },
        "profiles": []
    }

    # --- 6. CALCULATE RESISTANCE PROFILES ---
    surfaces = ["Concrete", "PET"]
    estimates = ["P5", "P50", "P95"]
    
    for surf_name in surfaces:
        for est in estimates:
            # Retrieve SSR/Prem inputs dynamically
            key_ssr = f"{surf_name}_{est}_SSR"
            key_prem = f"{surf_name}_{est}_Prem"
            
            SSR = inputs[key_ssr]
            Prem = inputs[key_prem]
            
            # Axial Breakout
            Abrk = alpha * SSR * (OCR**Prem) * zeta * rate * V
            
            # Axial Residual
            Ares = (1.0 / St) * Abrk
            
            # Lateral Breakout (Friction + Passive)
            Lbrk = (alpha * SSR * (OCR**Prem) * rate * V) + Fl_remain
            
            # Lateral Residual
            Lres_raw = (0.32 + 0.8 * (Z / Dop)**0.8) * V if Dop > 0 else 0
            
            # Apply safety factors to Residual
            if est == "P5":
                Lres = Lres_raw / 1.5
            elif est == "P95":
                Lres = Lres_raw * 1.5
            else:
                Lres = Lres_raw
                
            # Displacements Calculation
            Dop_mm = Dop * 1000.0
            
            if est == "P5":
                Xb = min(1.25, 0.0025 * Dop_mm)
                Xr = min(7.5, 0.015 * Dop_mm)
                Yb = (0.004 + 0.02 * (Z/Dop)) * Dop_mm
                Yr = 0.6 * Dop_mm
            elif est == "P50":
                Xb = min(5.0, 0.01 * Dop_mm)
                Xr = min(30.0, 0.06 * Dop_mm)
                Yb = (0.02 + 0.25 * (Z/Dop)) * Dop_mm
                Yr = 1.5 * Dop_mm
            else: # P95
                Xb = max(50.0, 0.01 * Dop_mm)
                Xr = max(250.0, 0.5 * Dop_mm)
                Yb = (0.1 + 0.7 * (Z/Dop)) * Dop_mm
                Yr = 2.8 * Dop_mm
                
            # Append to results list
            results["profiles"].append({
                "Surface": surf_name,
                "Estimate": est,
                "Axial": {"BreakForce": Abrk, "BreakDisp": Xb, "ResForce": Ares, "ResDisp": Xr},
                "Lateral": {"BreakForce": Lbrk, "BreakDisp": Yb, "ResForce": Lres, "ResDisp": Yr}
            })
            
    return results
