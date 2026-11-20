from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import pandas as pd
import plotly.express as px
import io
import math

app = Flask(__name__)
app.secret_key = "sales_dashboard_key"

REQUIRED_COLUMNS = [
    "Order_ID", "Order_Date", "Customer", "Product",
    "Category", "Region", "Quantity", "Unit_Price",
    "Discount", "Revenue", "Cost", "Profit", "Payment_Method"
]

df = pd.read_csv("data/cleaned_sales_data.csv")
df["Order_Date"] = pd.to_datetime(df["Order_Date"], errors="coerce")
df = df.dropna(subset=["Order_Date"])

active_df = df.copy()


def get_filtered_data():

    current_df = active_df.copy()

    selected_region = request.args.get("region", "All")
    selected_category = request.args.get("category", "All")

    start_date = (
        current_df["Order_Date"].min().strftime("%Y-%m-%d")
        if not current_df.empty else ""
    )

    end_date = (
        current_df["Order_Date"].max().strftime("%Y-%m-%d")
        if not current_df.empty else ""
    )

    selected_start = request.args.get("start_date", start_date)
    selected_end = request.args.get("end_date", end_date)

    if selected_region != "All":
        current_df = current_df[current_df["Region"] == selected_region]

    if selected_category != "All":
        current_df = current_df[current_df["Category"] == selected_category]

    if selected_start and selected_end:
        current_df = current_df[
            (current_df["Order_Date"] >= pd.to_datetime(selected_start)) &
            (current_df["Order_Date"] < pd.to_datetime(selected_end) + pd.Timedelta(days=1))
        ]

    return current_df


# CSV UPLOAD
@app.route("/upload", methods=["POST"])
def upload_file():
    global active_df

    file = request.files.get("file")

    if not file or file.filename == "":
        flash("Please select a CSV file.", "error")
        return redirect(url_for("home"))

    if not file.filename.lower().endswith(".csv"):
        flash("Only CSV files are allowed.", "error")
        return redirect(url_for("home"))

    try:
        uploaded_df = pd.read_csv(file)

        missing_columns = [
            column for column in REQUIRED_COLUMNS
            if column not in uploaded_df.columns
        ]

        if missing_columns:
            flash("Missing columns: " + ", ".join(missing_columns), "error")
            return redirect(url_for("home"))

        uploaded_df["Order_Date"] = pd.to_datetime(
            uploaded_df["Order_Date"], errors="coerce"
        )

        uploaded_df = uploaded_df.dropna(subset=["Order_Date"])

        numeric_columns = [
            "Quantity", "Unit_Price", "Discount",
            "Revenue", "Cost", "Profit"
        ]

        for column in numeric_columns:
            uploaded_df[column] = pd.to_numeric(
                uploaded_df[column], errors="coerce"
            )

        uploaded_df = uploaded_df.dropna(subset=numeric_columns)

        if uploaded_df.empty:
            flash("The uploaded file contains no valid sales records.", "error")
            return redirect(url_for("home"))

        active_df = uploaded_df.copy()

        flash(
            f"Dataset uploaded successfully! {len(active_df)} records loaded.",
            "success"
        )

    except Exception as e:
        flash(f"Unable to process file: {e}", "error")

    return redirect(url_for("home"))


# RESTORE DATASET
@app.route("/reset_data")
def reset_data():
    global active_df

    active_df = df.copy()
    flash("Original dataset restored successfully.", "success")

    return redirect(url_for("home"))


# DOWNLOAD CSV
@app.route("/download")
def download_csv():

    filtered_df = get_filtered_data()

    output = io.BytesIO()
    filtered_df.to_csv(output, index=False, encoding="utf-8-sig")
    output.seek(0)

    return send_file(
        output,
        mimetype="text/csv",
        as_attachment=True,
        download_name="sales_filtered_data.csv"
    )


# DASHBOARD
@app.route("/")
def home():

    current_df = active_df.copy()

    regions = sorted(current_df["Region"].dropna().unique().tolist())
    categories = sorted(current_df["Category"].dropna().unique().tolist())

    start_date = (
        current_df["Order_Date"].min().strftime("%Y-%m-%d")
        if not current_df.empty else ""
    )

    end_date = (
        current_df["Order_Date"].max().strftime("%Y-%m-%d")
        if not current_df.empty else ""
    )

    selected_region = request.args.get("region", "All")
    selected_category = request.args.get("category", "All")
    selected_start = request.args.get("start_date", start_date)
    selected_end = request.args.get("end_date", end_date)

    filtered_df = get_filtered_data()

    # KPI CALCULATIONS
    total_revenue = filtered_df["Revenue"].sum()
    total_profit = filtered_df["Profit"].sum()
    total_orders = filtered_df["Order_ID"].nunique()
    total_quantity = filtered_df["Quantity"].sum()

    profit_margin = (
        (total_profit / total_revenue) * 100
        if total_revenue != 0 else 0
    )

    average_order_value = (
        total_revenue / total_orders if total_orders != 0 else 0
    )

    average_profit_per_order = (
        total_profit / total_orders if total_orders != 0 else 0
    )

    # MONTHLY REVENUE
    monthly_sales = (
        filtered_df.groupby(filtered_df["Order_Date"].dt.to_period("M"))["Revenue"]
        .sum()
        .reset_index()
    )

    monthly_sales["Month"] = monthly_sales["Order_Date"].astype(str)

    fig = px.line(
        monthly_sales,
        x="Month",
        y="Revenue",
        markers=True,
        title="Monthly Revenue Trend"
    )

    fig.update_layout(
        template="plotly_white",
        height=450,
        autosize=True,
        xaxis_title="Month",
        yaxis_title="Revenue (₹)",
        margin=dict(l=40, r=30, t=60, b=50)
    )

    monthly_chart = fig.to_html(
        full_html=False,
        include_plotlyjs="cdn",
        config={"responsive": True}
    )

    # CATEGORY CHART
    category_sales = (
        filtered_df.groupby("Category")["Revenue"]
        .sum()
        .reset_index()
    )

    fig2 = px.bar(
        category_sales,
        x="Category",
        y="Revenue",
        color="Category",
        title="Revenue by Category"
    )

    fig2.update_layout(
        template="plotly_white",
        height=420,
        autosize=True,
        xaxis_title="Category",
        yaxis_title="Revenue (₹)",
        margin=dict(l=50, r=30, t=70, b=60)
    )

    category_chart = fig2.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"responsive": True}
    )

    # REGION CHART
    region_sales = (
        filtered_df.groupby("Region")["Revenue"]
        .sum()
        .reset_index()
    )

    fig3 = px.bar(
        region_sales,
        x="Region",
        y="Revenue",
        color="Region",
        title="Revenue by Region"
    )

    fig3.update_layout(
        template="plotly_white",
        height=420,
        autosize=True,
        xaxis_title="Region",
        yaxis_title="Revenue (₹)",
        margin=dict(l=50, r=30, t=70, b=60)
    )

    region_chart = fig3.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"responsive": True}
    )

    # TOP 10 PRODUCTS
    product_sales = (
        filtered_df.groupby("Product")["Revenue"]
        .sum()
        .reset_index()
        .sort_values(by="Revenue", ascending=False)
        .head(10)
    )

    fig4 = px.bar(
        product_sales,
        x="Revenue",
        y="Product",
        orientation="h",
        title="Top 10 Products by Revenue",
        color="Revenue"
    )

    fig4.update_layout(
        template="plotly_white",
        height=500,
        autosize=True,
        xaxis_title="Revenue (₹)",
        yaxis_title="Product",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=50, r=30, t=70, b=50)
    )

    product_chart = fig4.to_html(
        full_html=False,
        include_plotlyjs=False,
        config={"responsive": True}
    )

    # MONTHLY GROWTH ANALYSIS
    growth_df = pd.DataFrame()
    growth_chart = ""
    current_growth = 0
    growth_status = "No Data"

    if not filtered_df.empty:

        monthly_growth = (
            filtered_df.groupby(filtered_df["Order_Date"].dt.to_period("M"))["Revenue"]
            .sum()
        )

        # Create continuous monthly periods
        full_months = pd.period_range(
            filtered_df["Order_Date"].min().to_period("M"),
            filtered_df["Order_Date"].max().to_period("M"),
            freq="M"
        )

        monthly_growth = monthly_growth.reindex(full_months, fill_value=0)

        growth_df = pd.DataFrame({
            "Month": monthly_growth.index.astype(str),
            "Revenue": monthly_growth.values
        })

        growth_df["Previous_Revenue"] = growth_df["Revenue"].shift(1)

        growth_df["Growth_Percentage"] = (
            (growth_df["Revenue"] - growth_df["Previous_Revenue"]) /
            growth_df["Previous_Revenue"].replace(0, float("nan"))
        ) * 100

        growth_df["Growth_Percentage"] = growth_df["Growth_Percentage"].fillna(0)

        if len(growth_df) >= 2:
            current_growth = float(
                growth_df.iloc[-1]["Growth_Percentage"]
            )

            if current_growth > 0:
                growth_status = "Growth"
            elif current_growth < 0:
                growth_status = "Decline"
            else:
                growth_status = "No Change"

        fig5 = px.bar(
            growth_df,
            x="Month",
            y="Growth_Percentage",
            title="Monthly Revenue Growth (%)",
            labels={
                "Growth_Percentage": "Growth (%)",
                "Month": "Month"
            }
        )

        fig5.update_layout(
            template="plotly_white",
            height=420,
            autosize=True,
            xaxis_title="Month",
            yaxis_title="Growth (%)",
            margin=dict(l=50, r=30, t=70, b=60)
        )

        growth_chart = fig5.to_html(
            full_html=False,
            include_plotlyjs=False,
            config={"responsive": True}
        )

    # BUSINESS INSIGHTS
    insights = []

    if not filtered_df.empty:

        if not category_sales.empty:
            best_category = category_sales.loc[
                category_sales["Revenue"].idxmax()
            ]

            insights.append(
                f"Top revenue-generating category is "
                f"{best_category['Category']} with revenue of "
                f"₹{best_category['Revenue']:,.2f}."
            )

        if not region_sales.empty:
            best_region = region_sales.loc[
                region_sales["Revenue"].idxmax()
            ]

            insights.append(
                f"{best_region['Region']} is the leading region "
                f"with revenue of ₹{best_region['Revenue']:,.2f}."
            )

        if not product_sales.empty:
            best_product = product_sales.iloc[0]

            insights.append(
                f"Top product is {best_product['Product']} "
                f"with revenue of ₹{best_product['Revenue']:,.2f}."
            )

        insights.append(
            f"Overall profit margin is {profit_margin:.2f}%."
        )

        insights.append(
            f"Average revenue per order is ₹{average_order_value:,.2f}."
        )

        if len(growth_df) >= 2:
            insights.append(
                f"Latest monthly revenue growth is {current_growth:.2f}% "
                f"({growth_status.lower()})."
            )

    else:
        insights.append("No sales data available for the selected filters.")

    # SEARCH TABLE
    search_query = request.args.get("search", "").strip()

    table_df = filtered_df.copy()

    if search_query:
        searchable_columns = [
            "Order_ID", "Customer", "Product",
            "Category", "Region", "Payment_Method"
        ]

        search_mask = table_df[searchable_columns].astype(str).apply(
            lambda row: row.str.contains(
                search_query, case=False, na=False
            ).any(),
            axis=1
        )

        table_df = table_df[search_mask]

    table_df = table_df.sort_values("Order_Date", ascending=False)

    # PAGINATION
    page = request.args.get("page", 1, type=int)
    page_size = 10

    total_table_records = len(table_df)
    total_pages = max(1, math.ceil(total_table_records / page_size))

    page = min(max(page, 1), total_pages)

    start_index = (page - 1) * page_size
    end_index = start_index + page_size

    page_df = table_df.iloc[start_index:end_index].copy()

    page_df["Order_Date"] = page_df["Order_Date"].dt.strftime("%d-%m-%Y")

    table_records = page_df.to_dict(orient="records")

    return render_template(
        "index.html",

        total_revenue=total_revenue,
        total_profit=total_profit,
        total_orders=total_orders,
        total_quantity=total_quantity,

        profit_margin=profit_margin,
        average_order_value=average_order_value,
        average_profit_per_order=average_profit_per_order,

        current_growth=current_growth,
        growth_status=growth_status,
        growth_chart=growth_chart,
        growth_records=growth_df.to_dict(orient="records"),

        monthly_chart=monthly_chart,
        category_chart=category_chart,
        region_chart=region_chart,
        product_chart=product_chart,

        insights=insights,

        regions=regions,
        categories=categories,

        selected_region=selected_region,
        selected_category=selected_category,
        selected_start=selected_start,
        selected_end=selected_end,

        start_date=start_date,
        end_date=end_date,

        table_records=table_records,
        search_query=search_query,
        page=page,
        total_pages=total_pages,
        total_table_records=total_table_records
    )


if __name__ == "__main__":
    app.run(debug=True)
