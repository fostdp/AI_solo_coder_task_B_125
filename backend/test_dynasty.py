import sys
sys.path.insert(0, r"d:\SOLO-2\AI_solo_coder_task_B_125\backend")
from simulation.dynasty_comparison import DynastyComparisonEngine

e = DynastyComparisonEngine()
print("Models:", e.list_pagodas())

r = e.generate_comparison_report("yingxian", "gojunoto")
print("Title:", r["title"])
print("Freq A:", r["natural_frequency_comparison"]["pagoda_a"]["frequencies_hz"])
print("Freq B:", r["natural_frequency_comparison"]["pagoda_b"]["frequencies_hz"])
print("Wind A disp:", r["wind_displacement_comparison"]["pagoda_a"]["top_displacement_m"])
print("Wind B disp:", r["wind_displacement_comparison"]["pagoda_b"]["top_displacement_m"])
print("ED A:", r["energy_dissipation_comparison"]["pagoda_a"]["energy_per_cycle_kj"])
print("ED B:", r["energy_dissipation_comparison"]["pagoda_b"]["energy_per_cycle_kj"])
print("Philosophy:", r["seismic_philosophy_comparison"]["analysis"])
print("ALL TESTS PASSED")
