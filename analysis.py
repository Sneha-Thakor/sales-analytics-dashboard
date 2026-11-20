import pandas as pd
import os

# Load dataset
df = pd.read_csv("data/sales_data.csv")

print("=" * 50)
print("SALES DATA ANALYSIS - DATA EXPLORATION")
print("=" * 50)

# 1. Dataset overview
print("\n1. Dataset Shape:")
print(df.shape)

print("\n2. First 5 Records:")
print(df.head())

print("\n3. Column Names:")
print(df.columns.tolist())

print("\n4. Data Types:")
print(df.dtypes)

# 2. Missing values
print("\n5. Missing Values:")
print(df.isnull().sum())

# 3. Duplicate records
print("\n6. Duplicate Records:")
print(df.duplicated().sum())

# 4. Data cleaning
df.drop_duplicates(inplace=True)

df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")

# Handle missing values
df.dropna(subset=["Order_Date"], inplace=True)

# 5. Save cleaned data
os.makedirs("data", exist_ok=True)
df.to_csv("data/cleaned_sales_data.csv", index=False)

print("\n7. Cleaned Dataset Shape:")
print(df.shape)

print("\n8. Statistical Summary:")
print(df.describe())

print("\n" + "=" * 50)
print("DATA CLEANING COMPLETED SUCCESSFULLY!")
print("Cleaned file saved: data/cleaned_sales_data.csv")
print("=" * 50)
