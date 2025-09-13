import numpy as np
import pandas as pd

# Load data
data = pd.read_csv('simulation_duration_20kmh.csv')
x = data['SimulatedTime(s)'].values
y = data['RealTime(s)'].values

# Fit a polynomial of chosen degree (e.g. degree = 3)
degree = 3
coeffs = np.polyfit(x, y, degree)
poly = np.poly1d(coeffs)

# Compute first and second derivatives
poly_der1 = np.polyder(poly, 1)
poly_der2 = np.polyder(poly, 2)

# Print out the fitted function and its derivatives
print("Fitted polynomial (degree {}):".format(degree))
print(poly)         

print("\nFirst derivative f'(x):")
print(poly_der1)   

print("\nSecond derivative f''(x):")
print(poly_der2)
