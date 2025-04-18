import pandas as pd
import matplotlib.pyplot as plt

def plot_illuminance(df):
    """
    df: pandas DataFrame with columns 'Latitude', 'Longitude', and 'lux'
    Plots illuminance over the region 125°E–130°E, 32.5°N–38.5°N.
    """
    # Filter the region
    mask = (
        (df['Longitude'] >= 125.0) & (df['Longitude'] <= 130.0) &
        (df['Latitude']  >=  32.5) & (df['Latitude']  <=  38.5)
    )
    subset = df[mask]

    # Create scatter plot
    plt.figure(figsize=(10, 8))
    scatter = plt.scatter(
        subset['Longitude'],
        subset['Latitude'],
        c=subset['lux'],
        s=2
    )
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.colorbar(scatter, label='Illuminance (lux)')
    plt.title('Illuminance over 125–130°E, 32.5–38.5°N')
    plt.show()

def main():
    # Replace with your CSV file path
    csv_file = 'assets/2025041423.csv'
    
    # Read the CSV (expects columns: Latitude, Longitude, lux)
    df = pd.read_csv(csv_file)
    
    # Plot
    plot_illuminance(df)

if __name__ == "__main__":
    main()
