import math
import pandas as pd

class PSI_Undrained_Model:
    def __init__(self, dop, tp, z, su, ocr, st, alpha, rate, sub_wt_raw, 
                 ssr_conc, prem_conc, ssr_pet, prem_pet):
        """
        Initialize the model with all physical inputs.
        """
        self.dop = dop        # Outer Diameter (m)
        self.tp = tp          # Wall Thickness (m)
        self.z = z            # Embedment Depth (m)
        self.su = su          # Undrained Shear Strength (kPa)
        self.ocr = ocr        # Over Consolidation Ratio
        self.st = st          # Sensitivity
        self.alpha = alpha    # Adhesion Factor
        self.rate = rate      # Displacement Rate
        self.sub_wt = sub_wt_raw - 10.05  # Effective submerged unit weight adjustment (from VBA)
        
        # Coefficients [Low, Best, High]
        self.ssr_conc = ssr_conc
        self.prem_conc = prem_conc
        self.ssr_pet = ssr_pet
        self.prem_pet = prem_pet

        # Constants
        self.g = 9.8
        self.klay = 2.0
        self.rho_steel = 7850
        self.rho_conc = 1000  # From VBA logic (though typically 2400, VBA used 1000 for Wcon calc)
        self.rho_sw = 1025    # Seawater density

    def calculate_weights(self):
        dip = self.dop - 2 * self.tp
        
        # Weight Calculations
        wp = (math.pi * (self.dop**2 - dip**2) * self.rho_steel) / 4
        wcon = (math.pi * (dip**2) * self.rho_conc) / 4
        wb = (math.pi * (self.dop**2) * self.rho_sw) / 4
        
        # Flooded weight in kN/m
        wpf = ((wp + wcon - wb) * self.g) / 1000
        
        # Installation weight param
        wpins = (math.pi * (self.dop**2 - dip**2) * (self.rho_steel - self.rho_sw)) / 4
        
        # Effective Vertical Force (V)
        v = max((wpins * self.klay * self.g / 1000), wpf)
        
        return {
            "Wp": wp, "Wpf": wpf, "V": v, "Dip": dip
        }

    def calculate_geometry_and_resistance(self, v):
        # Geometric Parameters
        if self.z < (self.dop / 2):
            b_width = 2 * math.sqrt(self.dop * self.z - self.z**2)
            # Area of immersed segment
            term1 = math.asin(b_width / self.dop) * (self.dop**2 / 4)
            term2 = (b_width * (self.dop / 4) * math.cos(math.asin(b_width / self.dop)))
            abm = term1 - term2
        else:
            b_width = self.dop
            abm = (math.pi * self.dop**2 / 8) + self.dop * (self.z - self.dop / 2)

        # Vertical Penetration Resistance (Qv)
        term_bearing = min(6 * (self.z / self.dop)**0.25, 3.4 * (10 * self.z / self.dop)**0.5)
        term_bouyancy = (1.5 * self.sub_wt * abm / (self.dop * self.su))
        qv = (term_bearing + term_bouyancy) * self.dop * self.su

        # Wedging Factors
        cos_val = 1 - self.z / (self.dop / 2)
        # Clamp value to domain of acos [-1, 1]
        cos_val = max(-1, min(1, cos_val))
        
        beta = math.acos(cos_val)
        
        # Avoid division by zero if beta is 0
        if beta == 0:
            zeta = 1
        else:
            zeta = (2 * math.sin(beta)) / (beta + math.sin(beta) * math.cos(beta))
            
        fl_remain = self.z * self.rate * (2 * self.su + 0.5 * self.sub_wt * self.z) # Note: VBA used Range("B14") for Su in formula, assumed Su here.

        return {
            "Abm": abm, "Qv": qv, "zeta": zeta, "Fl_remain": fl_remain
        }

    def run_simulation(self):
        weights = self.calculate_weights()
        v = weights["V"]
        geo = self.calculate_geometry_and_resistance(v)
        
        results = []
        estimates = ["Low Estimate-P5", "Best Estimate-P50", "High Estimate-P95"]
        
        # Iterate Surfaces: 1=Concrete, 2=PET
        surfaces = [
            ("Concrete", self.ssr_conc, self.prem_conc),
            ("PET", self.ssr_pet, self.prem_pet)
        ]
        
        for surf_name, ssr_list, prem_list in surfaces:
            for j in range(3): # 0, 1, 2 for Low, Best, High
                est_name = estimates[j]
                ssr = ssr_list[j]
                prem = prem_list[j]
                
                # Breakout and Residual Forces
                abrk = self.alpha * ssr * (self.ocr ** prem) * geo["zeta"] * self.rate * v
                ares = (1 / self.st) * abrk
                lbrk = (self.alpha * ssr * (self.ocr ** prem) * self.rate * v) + geo["Fl_remain"]
                
                # Lateral Residual Calculation
                base_lres = (0.32 + 0.8 * (self.z / self.dop)**0.8) * v
                if j == 0: # Low
                    lres = base_lres / 1.5
                elif j == 2: # High
                    lres = base_lres * 1.5
                else:
                    lres = base_lres
                
                # Displacement Calculations (converting m to mm logic from VBA)
                dop_mm = self.dop * 1000
                
                # Xb (Axial Break Displacement)
                if j == 0: xb = min(1.25, 0.0025 * dop_mm)
                elif j == 1: xb = min(5, 0.01 * dop_mm)
                else: xb = max(50, 0.01 * dop_mm)
                
                # Xr (Axial Res Displacement)
                if j == 0: xr = min(7.5, 0.015 * dop_mm)
                elif j == 1: xr = min(30, 0.06 * dop_mm)
                else: xr = max(250, 0.5 * dop_mm)
                
                # Yb (Lateral Break Displacement)
                if j == 0: yb = (0.004 + 0.02 * (self.z / self.dop)) * dop_mm
                elif j == 1: yb = (0.02 + 0.25 * (self.z / self.dop)) * dop_mm
                else: yb = (0.1 + 0.7 * (self.z / self.dop)) * dop_mm
                
                # Yr (Lateral Res Displacement)
                if j == 0: yr = 0.6 * dop_mm
                elif j == 1: yr = 1.5 * dop_mm
                else: yr = 2.8 * dop_mm

                results.append({
                    "Surface": surf_name,
                    "Estimate": est_name,
                    "Axial Brk (kN/m)": round(abrk, 2),
                    "Xbrk (mm)": round(xb, 2),
                    "Axial Res (kN/m)": round(ares, 2),
                    "Xres (mm)": round(xr, 2),
                    "Lat Brk (kN/m)": round(lbrk, 2),
                    "Ybrk (mm)": round(yb, 2),
                    "Lat Res (kN/m)": round(lres, 2),
                    "Yres (mm)": round(yr, 2)
                })
                
        return weights, geo, pd.DataFrame(results)
