import math
import pandas as pd

class Trenched_PSI_Backend:
    def __init__(self, dop, tp, h):
        """
        Initializes the model with constant physical inputs for the pipe and trench.
        
        Args:
            dop (float): Outer Diameter (m)
            tp (float): Wall Thickness (m)
            h (float): Trench Height / Soil Cover Height (m)
        """
        self.dop = dop
        self.tp = tp
        self.h = h

        # Constants
        self.pi = math.pi
        self.g_steel = 7850
        self.g_fluid = 1000
        self.g_sw = 1025
        self.g_acc = 9.8
        self.klay = 2.0
        self.nc = 9.0

    def calculate_weights(self):
        """Calculates pipe weights and effective vertical force (V)."""
        dip = self.dop - (2 * self.tp)
        
        # Area (used in uplift later, but calculated here in VBA context)
        ap = (self.pi * self.dop**2) / 4
        
        # Weight Calculations
        # Wp: Steel weight
        wp = (self.pi * (self.dop**2 - dip**2) * self.g_steel) / 4
        
        # Wcon: Fluid content weight
        wcon = (self.pi * (dip**2) * self.g_fluid) / 4
        
        # Wb: Buoyancy
        wb = (self.pi * (self.dop**2) * self.g_sw) / 4
        
        # Wpf: Flooded weight in kN/m
        wpf = ((wp + wcon - wb) * self.g_acc) / 1000
        
        # Wpins: Installation weight (Steel - Seawater)
        wpins = ((self.pi * (self.dop**2 - dip**2) * (self.g_steel - self.g_sw)) / 4) * self.g_acc / 1000
        
        # V: Effective Vertical Force
        v = max(wpins * self.klay, wpf)
        
        return {
            "V": v,
            "Dip": dip,
            "Ap": ap
        }

    def run_analysis(self, soil_inputs):
        """
        Runs the simulation for P5, P50, and P95 cases.
        
        Args:
            soil_inputs (dict): A dictionary containing lists for P5, P50, P95 values.
                                Keys: 'alpha', 'g_bulk', 's_bnb', 's_bo', 's_ba'
                                Each key maps to a list [val_p5, val_p50, val_p95]
        """
        weights = self.calculate_weights()
        v = weights["V"]
        ap = weights["Ap"]
        
        results = []
        estimates = ["P5 (Low)", "P50 (Best)", "P95 (High)"]
        
        # We loop 0 to 2 for the three estimate cases
        for i in range(3):
            # Extract inputs for this iteration
            alpha = soil_inputs['alpha'][i]
            g_bulk = soil_inputs['g_bulk'][i]
            
            # Calculate submerged unit weight
            g_sub = g_bulk - 10.05
            
            s_bnb = soil_inputs['s_bnb'][i]
            s_bo = soil_inputs['s_bo'][i]
            s_ba = soil_inputs['s_ba'][i]
            
            # --- Axial Resistance ---
            fa_deep = alpha * s_bnb * self.pi * self.dop
            fa_shallow = alpha * s_bo * (self.pi * self.dop / 2) + 2 * s_ba * (self.h + self.dop / 2)
            axial_gov = min(fa_deep, fa_shallow)
            
            # --- Uplift Resistance ---
            # FU_local calculation
            fu_local = (self.nc * s_bnb * self.dop) - (g_sub * ap)
            
            # FU_global calculation
            term1 = g_sub * self.h * self.dop
            term2 = g_sub * (self.dop**2) * (0.5 - self.pi / 8)
            term3 = 2 * s_bnb * (self.h + self.dop / 2)
            fu_global = term1 + term2 + term3
            
            uplift_gov = min(fu_local, fu_global)
            
            results.append({
                "Category": estimates[i],
                "Axial Resistance (kN/m)": round(axial_gov, 2),
                "Uplift Resistance (kN/m)": round(uplift_gov, 2)
            })
            
        return v, pd.DataFrame(results)
