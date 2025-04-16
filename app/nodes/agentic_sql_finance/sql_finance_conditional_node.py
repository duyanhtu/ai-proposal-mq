

from app.nodes.states.state_finance import StateSqlFinance

class SQLFinanceConditionalNodeV1:
    """
        SQLFinanceConditionalNodeV1: 
            Kiểm tra xem dữ liệu về tài chính đã được trích xuất có dữ liệu hay không.
        
        Args:
            name (str): Tên của node.
            supervisor_node (str): Tên của node giám sát.
            generate_excel_and_docx_node (str): Tên của node xuất file excel hoặc file docx.
        
        Returns:
            Node: Trả về một trong hai node: supervisor_node hoặc generate_excel_and_docx_node.
    """
    def __init__(self, name: str, supervisor_node: str, generate_excel_and_docx_node: str):
        self.name = name
        self.supervisor_node = supervisor_node
        self.generate_excel_and_docx_node = generate_excel_and_docx_node

    def __call__(self, state: StateSqlFinance):
        print(self.name)
        if state["is_data_extracted_finance"]:
            print("Route Supervisor Node")
            return self.supervisor_node
        print("Route Generate Excel And Docx Node")
        return self.generate_excel_and_docx_node