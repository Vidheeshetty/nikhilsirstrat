from backtest_utils.report_generator import ReportGenerator
import json

class MyNSEStrategyReportGenerator(ReportGenerator):
    """
    A strategy-specific report generator for MyNSEStrategy.
    """
    def save_aggregated_results(self, aggregated_summary: dict, output_dir: str):
        """
        Saves the aggregated results to a JSON file.
        """
        output_file = f"{output_dir}/aggregated_results.json"
        with open(output_file, 'w') as f:
            json.dump(aggregated_summary, f, indent=4)
        print(f"Aggregated results saved to {output_file}") 