from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from app.nodes.states.state_proposal_v1 import StateProposalV1

class LLMHRMergeNode:
    """
    Node xử lý việc gộp và so sánh yêu cầu nhân sự từ 2 JSON HR.
    """

    def __init__(self, name : str, llm: ChatOpenAI):
        self.name = name
        self.llm = llm

        # Tạo sẵn PromptTemplate để tránh tạo lại mỗi vòng lặp
        self.system_prompt_template = PromptTemplate.from_template(
        """
            Bạn là một chuyên gia phân tích và so sánh dữ liệu đầu vào.
            Dưới đây là hai JSON chứa yêu cầu nhân sự (HR) cho các vị trí khác nhau.Hãy phân tích và xác định các yêu cầu nhân sự từ hai JSON này. 
            **Yêu cầu xử lý:**
                + Nếu một vị trí chỉ có trong một JSON, hãy giữ nguyên vị trí đó và gộp chúng lại.
                + Nếu có sự trùng lặp giữa hai JSON:
                    - So sánh chi tiết từng trường: yêu cầu bằng cấp, số lượng, kinh nghiệm, chứng chỉ, v.v.
                    - Ưu tiên giữ lại thông tin chi tiết hơn, đầy đủ hơn hoặc hợp lý hơn giữa hai nguồn.
                    - Nếu thông tin từ cả hai nguồn đều hữu ích, hãy gộp lại có cấu trúc.
            
            **Ví dụ:**
            *Ví dụ 1: Trùng yêu cầu và mô tả:
                INPUT:
                    JSON A: "result_extraction_hr": {{"hr": [{{"position": "Kỹ sư mạng","quantity": "2","requirements": [{{"name": "Bằng cấp","description": "Tốt nghiệp đại học ngành CNTT."}}]}}]}},
                    JSON B: "result_extraction_technology": {{"hr": [{{"position": "Kỹ sư mạng","quantity": "2","requirements": [{{"name": "Bằng cấp","description": "Tốt nghiệp đại học ngành CNTT."}}]}}]}}
                OUTPUT:
                    {{"hr": [{{"position": "Kỹ sư mạng","quantity": "2","requirements": [{{"name": "Bằng cấp","description": "Tốt nghiệp đại học ngành CNTT."}}]}}]}}

            *Ví dụ 2: Trùng tên yêu cầu, mô tả khác:
                INPUT:
                    JSON A: "result_extraction_hr": {{"hr": [{{"position": "Lập trình viên","quantity": "3","requirements": [{{"name": "Kinh nghiệm","description": "Ít nhất 2 năm kinh nghiệm phát triển phần mềm."}}]}}]}},
                    JSON B: "result_extraction_technology": {{"hr": [{{"position": "Lập trình viên","quantity": "3","requirements": [{{"name": "Kinh nghiệm","description": "Đã từng tham gia phát triển hệ thống lớn sử dụng Python hoặc Java."}}]}}]}}
                OUTPUT:
                    {{"hr": [{{"position": "Lập trình viên","quantity": "3","requirements": [{{"name": "Kinh nghiệm","description": "• Ít nhất 2 năm kinh nghiệm phát triển phần mềm.\n• Đã từng tham gia phát triển hệ thống lớn sử dụng Python hoặc Java."}}]}}]}}
                
            *Ví dụ 3: Yêu cầu khác biệt:
                INPUT:
                    JSON A: "result_extraction_hr": {{"hr": [{{"position": "Quản trị hệ thống","quantity": "1","requirements": [{{"name": "Chứng chỉ","description": "Có chứng chỉ MCSA hoặc tương đương."}}]}}]}},
                    JSON B: "result_extraction_technology": {{"hr": [{{"position": "Quản trị hệ thống","quantity": "1","requirements": [{{"name": "Trình độ chuyên môn","description": "Tốt nghiệp đại học chuyên ngành Hệ thống thông tin."}}]}}]}}
                OUTPUT:
                    {{"hr": [{{"position": "Quản trị hệ thống","quantity": "1","requirements"{{"name": "Chứng chỉ","description": "Có chứng chỉ MCSA hoặc tương đươn{{"name": "Trình độ chuyên môn","description": "Tốt nghiệp đại học chuyên ngành Hệ thống thông ti}}]}}]}}
                    
            **Đầu vào:
                JSON A (Hồ sơ mời thầu HR):
                {result_extraction_hr}

                JSON B (Yêu cầu kỹ thuật HR):
                {result_extraction_technology}
            Kết luận: (Hãy đưa ra kết quả cuối cùng dựa trên phân tích của bạn)
        """)
        # self.system_prompt_template = PromptTemplate.from_template(
        #     """
        #     Bạn là một trợ lý AI chuyên phân tích, so sánh và tổng hợp các yêu cầu nhân sự (HR) từ nhiều nguồn khác nhau.
        #     Nhiệm vụ của bạn là nhận vào hai danh sách yêu cầu HR dưới dạng JSON (JSON A và JSON B) và tổng hợp chúng thành một danh sách yêu cầu HR cuối cùng, tuân thủ nghiêm ngặt các quy tắc sau:

        #     **Quy tắc tổng hợp:**

        #         1.  **Trùng cả yêu cầu và mô tả:** Nếu một yêu cầu (xác định bởi trường định danh chính) xuất hiện trong cả JSON A và JSON B VÀ tất cả các trường trong phần "mô tả" đều giống hệt nhau, chỉ giữ lại MỘT bản ghi duy nhất cho yêu cầu đó trong danh sách kết quả cuối cùng.
        #         2.  **Trùng yêu cầu, khác mô tả:** Nếu một yêu cầu (xác định bởi trường định danh chính) xuất hiện trong cả JSON A và JSON B nhưng phần "mô tả" (một hoặc nhiều trường) có sự khác biệt, hãy giữ lại MỘT bản ghi duy nhất cho yêu cầu đó. Trong bản ghi này, hãy kết hợp hoặc bổ sung thông tin từ cả hai nguồn vào phần mô tả để tạo ra một mô tả đầy đủ và chi tiết nhất có thể (ví dụ: gộp các điểm khác biệt, ưu tiên thông tin cụ thể hơn nếu có mâu thuẫn không thể gộp).
        #         3.  **Yêu cầu khác biệt:** Nếu một yêu cầu chỉ xuất hiện trong JSON A hoặc chỉ trong JSON B, hãy giữ nguyên bản ghi yêu cầu đó và đưa vào danh sách kết quả cuối cùng.

        #     **Đầu vào:**
        #         * JSON A (Ví dụ: từ Hồ sơ mời thầu HR):
        #             {result_extraction_hr}
        #         * JSON B (Ví dụ: từ Yêu cầu kỹ thuật HR):
        #             {result_extraction_technology}
                    
        #     **Kết quả mong muốn:**
        #         Hãy trả về một danh sách JSON duy nhất chứa tất cả các yêu cầu HR đã được tổng hợp theo các quy tắc trên. Mỗi phần tử trong danh sách JSON kết quả phải đại diện cho một yêu cầu HR cuối cùng.
        #         Ví dụ định dạng kết quả mong muốn:
        #         [
        #             {{"yeu_cau": "Yêu cầu HR cuối cùng 1", "mo_ta_tong_hop": "Mô tả đã được tổng hợp 1", ...}},
        #             {{"yeu_cau": "Yêu cầu HR cuối cùng 2", "mo_ta_tong_hop": "Mô tả đã được tổng hợp 2", ...}},
        #             ...
        #         ]

        #     (Lưu ý: Cấu trúc cụ thể của các đối tượng trong JSON kết quả nên giữ nguyên các trường cần thiết như yêu cầu, mô tả tổng hợp, số lượng, kinh nghiệm, v.v.)

        #     **Kết luận:** (Dựa trên phân tích và các quy tắc trên, hãy đưa ra danh sách JSON kết quả cuối cùng)
        #     """
        # )

    def __call__(self, state: StateProposalV1):
        # Lấy thông tin HR từ 2 JSON trong state
        result_extraction_hr = state.get("result_extraction_hr", {})
        result_extraction_technology = state.get("result_extraction_technology", {})
        # Kết nối prompt với LLM và xử lý kết quả
        chain = self.system_prompt_template | self.llm.with_structured_output(None, method="json_mode")
        result = chain.invoke({
            "result_extraction_hr": result_extraction_hr,
            "result_extraction_technology": result_extraction_technology,
        })
        return result
