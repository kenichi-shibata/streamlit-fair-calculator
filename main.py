import streamlit as st
from pyfair import FairModel
import streamlit.components.v1 as components
from pyecharts.charts import Bar
from pyecharts import options as opts
import numpy as np
import pandas as pd

def format_currency(value):
    """Helper function to format currency values."""
    return "${:,.2f}".format(value)

def calculate_summary_statistics(results):
    """
    Calculate summary statistics from FAIR model results.
    
    :param results: Dictionary containing FAIR model results.
    :return: Dictionary containing calculated statistics.
    """
    # Example structure for results: {'Loss Event Frequency': [values], 'Loss Magnitude': [values]}
    lef_values = results['Loss Event Frequency']
    lm_values = results['Loss Magnitude']
    
    # Primary stats
    primary_stats = {
        'Loss Events / Year': {
            'Min': np.min(lef_values),
            'Avg': np.mean(lef_values),
            'Max': np.max(lef_values)
        },
        'Loss Magnitude': {
            'Min': format_currency(np.min(lm_values)),
            'Avg': format_currency(np.mean(lm_values)),
            'Max': format_currency(np.max(lm_values))
        }
    }
    
    # Assuming secondary stats are calculated similarly or are placeholders
    secondary_stats = {
        'Loss Events / Year': {'Min': 0, 'Avg': 0, 'Max': 0},
        'Loss Magnitude': {'Min': 0, 'Avg': 0, 'Max': 0}
    }
    
    # Example calculation for vulnerability (this would depend on your specific model or criteria)
    vulnerability = np.mean(lef_values) * 100  # Example metric

    return primary_stats, secondary_stats, vulnerability


def display_statistics_in_streamlit(primary_stats, secondary_stats, vulnerability):
    """
    Display the calculated summary statistics in Streamlit.
    
    :param primary_stats: Dictionary with primary statistics.
    :param secondary_stats: Dictionary with secondary statistics.
    :param vulnerability: Float representing the vulnerability percentage.
    """
    # Display Primary Statistics
    st.subheader("Primary")
    primary_df = pd.DataFrame.from_dict(primary_stats, orient='index').rename(columns={0: 'Min', 1: 'Avg', 2: 'Max'})
    st.table(primary_df)

    # Display Secondary Statistics
    st.subheader("Secondary")
    secondary_df = pd.DataFrame.from_dict(secondary_stats, orient='index').rename(columns={0: 'Min', 1: 'Avg', 2: 'Max'})
    st.table(secondary_df)

    # Display Vulnerability
    st.subheader("Vulnerability")
    st.write(f"{vulnerability:.2f}%")


def display_fair_explanation():
    st.sidebar.header("About FAIR")
    st.sidebar.info(
        """
        The Factor Analysis of Information Risk (FAIR) is a methodology for understanding, analyzing, and quantifying information risk in financial terms. It helps organizations make better decisions about cybersecurity, risk management, and IT investments by providing a model to estimate the potential losses from risk events.
        """
    )

def display_input_explanations():
    st.sidebar.header("Input Explanations")
    st.sidebar.expander("Loss Event Frequency (LEF)", expanded=False).markdown(
        """
        - **LEF Min and Max**: Estimates of the minimum and maximum frequency of loss events per year. This helps in understanding the range of how often certain risk events might occur.
        """
    )
    st.sidebar.expander("Loss Magnitude (LM)", expanded=False).markdown(
        """
        - **LM Min and Max**: Estimates of the minimum and maximum potential loss from a single event. This range helps in assessing the financial impact of risk events.
        """
    )

def calculate_fair_model(lef_min, lef_max, lm_min, lm_max):
    lef_mean = (lef_min + lef_max) / 2
    lef_stdev = (lef_max - lef_min) / np.sqrt(12)
    lm_mode = (lm_min + lm_max) / 2

    model = FairModel(name='Basic Model', n_simulations=10_000)
    model.input_data('Loss Event Frequency', mean=lef_mean, stdev=lef_stdev)
    model.input_data('Loss Magnitude', low=lm_min, high=lm_max, mode=lm_mode)
    model.calculate_all()
    
    return model

def generate_ale_summary_chart(lef_summary, lm_summary, center):
    ale_summary = {f'{i}th_percentile':  lef_summary[f'{i}th_percentile'] * lm_summary[f'{i}th_percentile'] for i in range(1, 100)}
    rect_chart = Bar()
    labels = [f'{i}th-percentile' for i in range(1, 100)]
    rect_chart.add_xaxis(labels)
    rect_chart.add_yaxis("ALE (Combined Risk)", list(ale_summary.values()), gap=-0.2)
    rect_chart.set_global_opts(
        title_opts=opts.TitleOpts(title="FAIR Model ALE Summary"),
        tooltip_opts=opts.TooltipOpts(trigger="axis", axis_pointer_type="cross"),
        yaxis_opts=opts.AxisOpts(name="Dollars"),
        xaxis_opts=opts.AxisOpts(type_='category'),
        toolbox_opts=opts.ToolboxOpts(is_show=True),
    )
    rect_chart.set_series_opts(
        label_opts=opts.LabelOpts(is_show=False),
        itemstyle_opts=opts.ItemStyleOpts(color="#d94e5d")
    )

    html_content = rect_chart.render_embed()
    return html_content

def calculate_percentiles(values):
    return {f"{i}th_percentile": np.percentile(values, i) for i in range(1, 100)}

def main():
    st.title("FAIR Risk Calculation with PyFair and ECharts")
    display_fair_explanation()
    display_input_explanations()

    with st.form("model_input"):
        lef_min, lef_max = st.columns(2)
        with lef_min:
            lef_min_value = st.number_input("Loss Event Frequency Min", min_value=0.0, max_value=10.0, value=0.1, help="Enter the minimum estimated frequency of loss events per year.")
        with lef_max:
            lef_max_value = st.number_input("Loss Event Frequency Max", min_value=0.0, max_value=10.0, value=0.5, help="Enter the maximum estimated frequency of loss events per year.")

        lm_min, lm_max = st.columns(2)
        with lm_min:
            lm_min_value = st.number_input("Loss Magnitude Min", min_value=0, value=100000000, help="Enter the minimum estimated financial impact from a single event.")
        with lm_max:
            lm_max_value = st.number_input("Loss Magnitude Max", min_value=0, value=500000000, help="Enter the maximum estimated financial impact from a single event.")
        
        center = st.radio('Center of Analysis', ['mean', 'median'], help="Choose whether to center analysis on the mean or median of the distribution.")
        submitted = st.form_submit_button("Calculate Risk")

    if submitted:
        with st.spinner('Calculating...'):
            model = calculate_fair_model(lef_min_value, lef_max_value, lm_min_value, lm_max_value)
            results = model.export_results()
            lef_values = results['Loss Event Frequency']
            lm_values = results['Loss Magnitude']

            lef_summary = calculate_percentiles(lef_values)
            lm_summary = calculate_percentiles(lm_values)

            echarts_html_curve_summary = generate_ale_summary_chart(lef_summary, lm_summary, center)
            components.html(echarts_html_curve_summary, height=500, width=900)

            primary_stats, secondary_stats, vulnerability = calculate_summary_statistics(results)
            display_statistics_in_streamlit(primary_stats, secondary_stats, vulnerability)


if __name__ == "__main__":
    main()
