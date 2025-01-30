# Import necessary libraries
import matplotlib.pyplot as plt
import numpy as np
import tikzplotlib


# Define piecewise functions
def one_piece_function(x):
    if x <= 1:
        return 1  # Flat segment
    else:
        return 1 + 0.5 * (x - 1)  # Sloped segment


def two_piece_function(x):
    if x <= 1:
        return 1  # Flat segment
    elif x <= 1.8:
        return 1 + 0.5 * (x - 1)  # First slope
    else:
        return 1 + 0.5 * (1.8 - 1) + 0.9 * (x - 1.8)  # Second slope


def three_piece_function(x):
    if x <= 1:
        return 1  # Flat segment
    elif x <= 1.8:
        return 1 + 0.5 * (x - 1)  # First slope
    elif x <= 2:
        return 1 + 0.5 * (1.8 - 1) + 0.9 * (x - 1.8)  # Second slope
    else:
        return 1 + 0.5 * (1.8 - 1) + 0.9 * (2 - 1.8) + 1.1 * (x - 2)  # Third slope


def four_piece_function(x):
    if x <= 1:
        return 1  # Flat segment
    elif x <= 1.8:
        return 1 + 0.5 * (x - 1)  # First slope
    elif x <= 2:
        return 1 + 0.5 * (1.8 - 1) + 0.9 * (x - 1.8)  # Second slope
    elif x <= 2.4:
        return 1 + 0.5 * (1.8 - 1) + 0.9 * (2 - 1.8) + 1.1 * (x - 2)  # Third slope
    else:
        return 1 + 0.5 * (1.8 - 1) + 0.9 * (2 - 1.8) + 1.1 * (2.4 - 2) + 1.4 * (x - 2.4)  # Fourth slope


# Define the exponential function
def adjusted_exponential_function(x):
    return 1 + 0.075 * x ** 3


# Generate x values
x_values = np.linspace(0, 2.5, 300)

# Compute y values for all functions
y_values_1 = [one_piece_function(x) for x in x_values]
y_values_2 = [two_piece_function(x) for x in x_values]
y_values_3 = [three_piece_function(x) for x in x_values]
y_values_4 = [four_piece_function(x) for x in x_values]
y_values_exp = [adjusted_exponential_function(x) for x in x_values]

# Plot all functions with enhanced visualization
plt.figure(figsize=(12, 8))
plt.plot(x_values, y_values_1, label="K=1", linestyle="-", linewidth=2.2, marker="o", markevery=30)
plt.plot(x_values, y_values_2, label="K=2", linestyle="--", linewidth=2, marker="x", markevery=30)
plt.plot(x_values, y_values_3, label="K=3", linestyle="-.", linewidth=1.7, marker="s", markevery=30)
plt.plot(x_values, y_values_4, label="K=4", linestyle=":", linewidth=1.5, marker="^", markevery=30)
plt.plot(x_values, y_values_exp, label="Polynomial", linestyle="-", linewidth=1, color="red")

# Add labels, legend, and grid
plt.xlabel("x", fontsize=14)
plt.ylabel("tau(x)", fontsize=14)
plt.legend(fontsize=12, loc="upper left")
plt.grid(True, linestyle="--", alpha=0.6)


# Annotate exponential function


# Save plot as TikZ file
def save_plot_tikz(filename="pwl_comparison.tex"):
    tikzplotlib.save(filename, axis_width="\\textwidth", axis_height="0.7\\textwidth")


save_plot_tikz()
plt.savefig("pwl_comparison.pdf")
plt.show()


# Function to calculate metrics
def calculate_metrics(y_piecewise, y_exponential):
    absolute_error = np.abs(np.array(y_piecewise) - np.array(y_exponential))
    metrics = {
        "Mean Absolute Error (MAE)": np.mean(absolute_error),
        "Max Absolute Error": np.max(absolute_error),
        "Root Mean Squared Error (RMSE)": np.sqrt(np.mean(absolute_error ** 2)),
    }
    return metrics


# Calculate metrics for each function
metrics_1 = calculate_metrics(y_values_1, y_values_exp)
metrics_2 = calculate_metrics(y_values_2, y_values_exp)
metrics_3 = calculate_metrics(y_values_3, y_values_exp)
metrics_4 = calculate_metrics(y_values_4, y_values_exp)

# Print metrics in a tabular format
print("\nMetrics for Piecewise Functions (Compared to Polynomial):")
print(f"{'Function':<20}{'MAE':<15}{'Max Error':<15}{'RMSE':<15}")
print("-" * 50)
print(
    f"{'One-piece':<20}{metrics_1['Mean Absolute Error (MAE)']:<15.5f}{metrics_1['Max Absolute Error']:<15.5f}{metrics_1['Root Mean Squared Error (RMSE)']:<15.5f}")
print(
    f"{'Two-piece':<20}{metrics_2['Mean Absolute Error (MAE)']:<15.5f}{metrics_2['Max Absolute Error']:<15.5f}{metrics_2['Root Mean Squared Error (RMSE)']:<15.5f}")
print(
    f"{'Three-piece':<20}{metrics_3['Mean Absolute Error (MAE)']:<15.5f}{metrics_3['Max Absolute Error']:<15.5f}{metrics_3['Root Mean Squared Error (RMSE)']:<15.5f}")
print(
    f"{'Four-piece':<20}{metrics_4['Mean Absolute Error (MAE)']:<15.5f}{metrics_4['Max Absolute Error']:<15.5f}{metrics_4['Root Mean Squared Error (RMSE)']:<15.5f}")

# Calculate and display improvements
print("\nImprovements in Metrics:")


def improvement(previous, current):
    return {key: previous[key] - current[key] for key in previous}


def percentage_improvement(previous, current):
    return {key: (previous[key] - current[key]) / previous[key] * 100 if previous[key] != 0 else 0 for key in previous}


def pretty_print_improvements(previous_metrics, current_metrics, label):
    imp = improvement(previous_metrics, current_metrics)
    perc_imp = percentage_improvement(previous_metrics, current_metrics)
    print(f"{label:<20}{imp['Mean Absolute Error (MAE)']:<15.5f}{perc_imp['Mean Absolute Error (MAE)']:<15.2f}%" \
          f"{imp['Max Absolute Error']:<15.5f}{perc_imp['Max Absolute Error']:<15.2f}%" \
          f"{imp['Root Mean Squared Error (RMSE)']:<15.5f}{perc_imp['Root Mean Squared Error (RMSE)']:<15.2f}%")


print(
    f"{'From':<20}{'MAE Improvement':<15}{'MAE %':<15}{'Max Error Improvement':<15}{'Max Error %':<15}{'RMSE Improvement':<15}{'RMSE %':<15}")
print("-" * 90)
pretty_print_improvements(metrics_1, metrics_2, "1 to 2 pieces")
pretty_print_improvements(metrics_2, metrics_3, "2 to 3 pieces")
pretty_print_improvements(metrics_3, metrics_4, "3 to 4 pieces")

print(
    f"{'From':<20}{'MAE Improvement':<15}{'MAE %':<15}{'Max Error Improvement':<15}{'Max Error %':<15}{'RMSE Improvement':<15}{'RMSE %':<15}")
print("-" * 90)
pretty_print_improvements(metrics_1, metrics_2, "1 to 2 pieces")
pretty_print_improvements(metrics_1, metrics_3, "1 to 3 pieces")
pretty_print_improvements(metrics_1, metrics_4, "1 to 4 pieces")
