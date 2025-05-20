# Standard imports
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Third party imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_text_splitters import MarkdownTextSplitter

# Your imports
from app.model_ai import llm
from app.nodes.agentic_proposal.extraction_handle_error import format_error_message
from app.nodes.states.state_proposal_v1 import StateProposalV1
from app.utils.logger import get_logger

logger = get_logger("except_handling_extraction")

class ExtractionTechnologyNodeV2m0p0:
    """
        ExtractionTechnologyNodeV2m0p0
    """

    def __init__(self, name: str):
        self.name = name

    def __call__(self, state: StateProposalV1):
        print(self.name)
        try:
            chapter_content = state["document_content_markdown_hskt"]
            # Không có chương liên quan để bóc tách
            if len(chapter_content) < 1:
                return {
                    "result_extraction_technology": {},
                }
            # Load your Markdown file
            markdown_splitter = MarkdownTextSplitter(
                chunk_size=10000,
                chunk_overlap=200,
                keep_separator=False
            )
            chunks = markdown_splitter.split_text(chapter_content)

            def process_chunk(chunk, chunk_index):
                print(f"Processing chunk {chunk_index+1}/{len(chunks)}")
                chat_prompt_template = ChatPromptTemplate.from_template(
                    self._get_prompt_template())
                prompt = chat_prompt_template.invoke({"content": chunk})
                try:
                    response = llm.chat_model_gpt_4o_mini_16k().with_structured_output(
                        None, method="json_mode").invoke(prompt)
                    if isinstance(response, list):
                        return response
                    elif isinstance(response, dict) and response:
                        return [response]
                    return []
                except Exception as e:
                    print(f"Error processing chunk {chunk_index+1}: {str(e)}")
                    return []

            # max_workers = min(8, len(chunks))
            max_workers = 1
            all_results = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Create a MarkdownTextSplitter
                futures = [executor.submit(process_chunk, chunk, i)
                           for i, chunk in enumerate(chunks)]
                for future in futures:
                    chunk_results = future.result()
                    all_results.extend(chunk_results)
            merged_results = self._merge_technical_results(all_results)

            # merged = {
            #     "requirement_level_0": {
            #         "muc": "1.",
            #         "requirement_name": "Yêu cầu về kỹ thuật",
            #         "sub_requirements": []
            #     }
            # }

            # # Extract sub_requirements from the response
            # for item in merged_results:
            #     sub_reqs = item["requirement_level_0"].get("sub_requirements", [])
            #     merged["requirement_level_0"]["sub_requirements"].extend(sub_reqs)

            # return {"result_extraction_technology": merged}
            # Khởi tạo cấu trúc gộp
            merged = {
                "hr": [],
                "requirement_level_0": {
                    "muc": "1.",
                    "requirement_name": "Yêu cầu về kỹ thuật",
                    "sub_requirements": []
                }
            }

            # Tập hợp để theo dõi các mục duy nhất nhằm loại bỏ trùng lặp
            hr_seen = set()
            sub_req_muc_seen = set()

            # Gộp hr và sub_requirements từ các khối
            for item in merged_results:
                # Bỏ qua nếu item không hợp lệ
                if not isinstance(item, dict):
                    continue

                # Gộp hr
                hr_list = item.get("hr", [])
                for hr_item in hr_list:
                    # Tạo khóa duy nhất cho mục hr
                    hr_key = (
                        hr_item.get("position", ""),
                        hr_item.get("quantity", "0"),
                        tuple(
                            (req.get("name", ""), req.get("description", ""))
                            for req in hr_item.get("requirements", [])
                        )
                    )
                    if hr_key not in hr_seen:
                        hr_seen.add(hr_key)
                        merged["hr"].append(hr_item)

                # Gộp sub_requirements
                if "requirement_level_0" in item:
                    # sub_reqs = item["requirement_level_0"].get(
                    #     "sub_requirements", [])
                    # for sub_req in sub_reqs:
                    #     # Kiểm tra trùng lặp dựa trên muc của requirement_level_1
                    #     sub_muc = sub_req.get(
                    #         "requirement_level_1", {}).get("muc", "")
                    #     if sub_muc and sub_muc not in sub_req_muc_seen:
                    #         sub_req_muc_seen.add(sub_muc)
                    #         merged["requirement_level_0"]["sub_requirements"].append(
                    #             sub_req)
                    sub_reqs = item.get("requirement_level_0", {}).get("sub_requirements", [])
                    merged["requirement_level_0"]["sub_requirements"].extend(sub_reqs)
            # Sắp xếp để đảm bảo đầu ra nhất quán
            # merged["hr"].sort(key=lambda x: x["position"])
            # merged["requirement_level_0"]["sub_requirements"].sort(
            #     key=lambda x: x["requirement_level_1"]["muc"]
            # )
            return {"result_extraction_technology": merged}
        except Exception as e:
            error_msg = format_error_message(
                node_name=self.name,
                e=e,
                context=f"hs_id: {state.get('hs_id', '')}",
                include_trace=True
            )
            return {
                "result_extraction_technology": {},
                "error_messages": [error_msg],
            }

    def _get_prompt_template(self):
        """Return the prompt template for extraction"""
        return """
            Bạn là một chuyên gia trích xuất các yêu cầu của hồ sơ mời thầu.
            Hãy lấy tất cả các yêu cầu liên quan đến nhân sự và các yêu cầu còn lại bao gồm: yêu cầu kỹ thuật và các yêu cầu khác không liên quan đến nhân sự trong file được cung cấp.
            **CHÚ Ý:** PHẢI lấy đầy đủ nội dung yêu cầu và mô tả chi tiết yêu cầu trong tài liệu theo dữ liệu gốc.
                    Nếu trong file không có yêu cầu liên quan đến nhân sự thì để trống phần nhân sự.
                    Không lấy các thông tin về giới thiệu chung về gói thầu.
                    KHông lấy thông tin phạm vi gói thầu
                    KHÔNG tách nội dung mô tả để làm yêu cầu
                   
            2. Đối với dữ liệu yêu cầu trong bảng yêu cầu được viết trong 1 đoạn (ngăn cách bằng |   |) với
                - Nội dung cần trích xuất bắt đầu từ dấu `|` và kết thúc ngay trước dấu `|` tiếp theo (hoặc hết nội dung nếu không có dấu `|` tiếp theo).
                - Giữ nguyên toàn bộ nội dung gốc trong khoảng giữa hai dấu `|`, bao gồm cả định dạng văn bản, ký tự xuống dòng, hoặc ký tự đặc biệt nếu có, xóa dấu `|`.
                - Trong nội dung có các chú ý trong dấu () thì hãy lấy hết nội dung trong ngoặc đó như Điều khoản (3), Nghị định (8), Tiết (e), v.v.
                - Nếu dạng table thì mỗi row cho vào 1 description_detail riêng biệt.
                - KHông lấy tiêu đề cột trong bảng để làm yêu cầu.(ví dụ Thông số kỹ thuật/Yêu cầu dịch vụ  là tên cột của bảng yêu cầu cần bóc tách thì không đưa thành yêu cầu)
            3.Đối với dữ liệu không nằm trong bảng lấy yêu cầu theo heading( hoặc -)
            5. Bỏ qua các chỉ mục ví dụ 3.1, 3.2,.... và lấy đúng tên yêu cầu cần lấy.
           
            6. Ví dụ chỉ để tham khảo KHÔNG phải là nội dung cần bóc tách.
            7. Đầu ra hãy trả về dạng JSON.
 
            **Ví dụ**
            Ví dụ 1: có input như sau:
            **3.3 Yêu cầu nội dung công việc bảo trì**
            3.3.1 Yêu cầu chung

                -Kiểm tra, bảo trì định kỳ: Trong thời gian bảo trì, định kỳ tối thiểu 03 tháng/01 lần (hoặc ngay khi có yêu cầu của Agribank) thực hiện kiểm tra, bảo dưỡng định kỳ cho các thiết bị thuộc phạm vi bảo trì, rà soát cấu hình, đánh giá hiệu năng sử dụng, đưa ra các khuyến nghị để tối ưu thiết bị (nếu có).

                - Hỗ trợ kỹ thuật và xử lý, khắc phục sự cố: Trong thời gian bảo trì, đơn vị cung cấp dịch vụ bảo trì phải cung cấp dịch vụ hỗ trợ kỹ thuật và khắc phục sự cố thiết bị. Khi có yêu cầu hỗ trợ kỹ thuật của Agribank hoặc khi thiết bị có sự cố, đơn vị cung cấp dịch vụ bảo trì có trách nhiệm hỗ trợ kỹ thuật và xử lý, khắc phục sự cố; trường hợp cần thiết đơn vị cung cấp dịch vụ bảo trì phải cử cán bộ trực tiếp tới địa điểm lắp đặt thiết bị hoặc yêu cầu hỗ trợ trợ kỹ thuật của hãng sản xuất để xử lý và khắc phục sự cố trong thời gian sớm nhất.
                - Cập nhật phần mềm hệ điều hành và phần mềm an ninh phòng chống tấn công xâm nhập (IPS) của thiết bị: Trong thời gian bảo trì, các thiết bị phải được thường xuyên, liên tục cập nhập phần mềm hệ điều hành thiết bị, bản vá lỗi, phần mềm an ninh phòng chống tấn công xâm nhập và các mẫu tấn công xâm nhập mới theo tiêu chuẩn của hãng sản xuất. Căn cứ các khuyến nghị/khuyến cáo của hãng sản

                3

                xuất, yêu cầu của Agribank, đơn vị cung cấp phải chủ động tiến hành phân tích, lên kế hoạch để nâng cấp, cập nhật kịp thời nhằm giúp các thiết bị tường lửa hoạt động an toàn, ổn định, ngăn ngừa các lỗi và sự cố ảnh hưởng đến hoạt động hệ thống mạng.
            Output mong muốn như sau:
            [
                {{	"hr": [             
                    ]
                }},
                
                    {{ "requirement_level_0": {{
                        "muc": "3",
                        "requirement_name": "Yêu cầu về kỹ thuật",
                        "sub_requirements": [
                            {{
                                "requirement_level_1": {{
                                    "muc": "3.3",
                                    "requirement_name": "Yêu cầu nội dung công việc bảo trì",
                                    "sub_requirements": [
                                        {{
                                            "requirement_level_2": {{
                                                "muc": "3.3.1",
                                                "requirement_name": "Yêu cầu chung",
                                                "description": [
                                                    {{
                                                        "description_detail": "Kiểm tra, bảo trì định kỳ: Trong thời gian bảo trì, định kỳ tối thiểu 03 tháng/01 lần (hoặc ngay khi có yêu cầu của Agribank) thực hiện kiểm tra, bảo dưỡng định kỳ cho các thiết bị thuộc phạm vi bảo trì, rà soát cấu hình, đánh giá hiệu năng sử dụng, đưa ra các khuyến nghị để tối ưu thiết bị (nếu có)."
                                                    }},
                                                    {{
                                                        "description_detail": "Hỗ trợ kỹ thuật và xử lý, khắc phục sự cố: Trong thời gian bảo trì, đơn vị cung cấp dịch vụ bảo trì phải cung cấp dịch vụ hỗ trợ kỹ thuật và khắc phục sự cố thiết bị. Khi có yêu cầu hỗ trợ kỹ thuật của Agribank hoặc khi thiết bị có sự cố, đơn vị cung cấp dịch vụ bảo trì có trách nhiệm hỗ trợ kỹ thuật và xử lý, khắc phục sự cố; trường hợp cần thiết đơn vị cung cấp dịch vụ bảo trì phải cử cán bộ trực tiếp tới địa điểm lắp đặt thiết bị hoặc yêu cầu hỗ trợ trợ kỹ thuật của hãng sản xuất để xử lý và khắc phục sự cố trong thời gian sớm nhất."
                                                    }},
                                                    {{
                                                        "description_detail": "Cập nhật phần mềm hệ điều hành và phần mềm an ninh phòng chống tấn công xâm nhập (IPS) của thiết bị: Trong thời gian bảo trì, các thiết bị phải được thường xuyên, liên tục cập nhập phần mềm hệ điều hành thiết bị, bản vá lỗi, phần mềm an ninh phòng chống tấn công xâm nhập và các mẫu tấn công xâm nhập mới theo tiêu chuẩn của hãng sản xuất. Căn cứ các khuyến nghị/khuyến cáo của hãng sản xuất, yêu cầu của Agribank, đơn vị cung cấp phải chủ động tiến hành phân tích, lên kế hoạch để nâng cấp, cập nhật kịp thời nhằm giúp các thiết bị tường lửa hoạt động an toàn, ổn định, ngăn ngừa các lỗi và sự cố ảnh hưởng đến hoạt động hệ thống mạng."
                                                    }}
                                                ]
                                            }}
                                        }},
                                        {{
                                            "requirement_level_2": {{
                                                "muc": "3.3.2",
                                                "requirement_name": "Yêu cầu về công việc kiểm tra, bảo trì định kỳ",
                                                "sub_requirements": [
                                                    {{
                                                        "requirement_level_3": {{
                                                            "muc": "a",
                                                            "requirement_name": "Kiểm tra, vệ sinh thiết bị",
                                                            "description": [
                                                                {{
                                                                    "description_detail": "Kiểm tra môi trường hoạt động của thiết bị, nguồn điện, nhiệt độ."
                                                                }},
                                                                {{
                                                                    "description_detail": "Kiểm tra dây cáp, đầu kết nối mạng. Sắp xếp gọn gàng và cố định các dây cáp kết nối mạng trên thiết bị."
                                                                }},
                                                                {{
                                                                    "description_detail": "Thực hiện bảo dưỡng, vệ sinh thiết bị, nguồn, cổng kết nối, module SFP."
                                                                }}
                                                            ]
                                                        }}
                                                    }},
                                                    {{
                                                        "requirement_level_3": {{
                                                            "muc": "b",
                                                            "requirement_name": "Kiểm tra hoạt động, cấu hình và chính sách an ninh của thiết bị",
                                                            "description": [
                                                                {{
                                                                    "description_detail": "Kiểm tra hiệu năng hoạt động của thiết bị: khả năng đáp ứng tài nguyên của bộ vi xử lý (CPU) và bộ nhớ (RAM)."
                                                                }}
                                                            ]
                                                        }}
                                                    }},
                                                    {{
                                                        "requirement_level_3": {{
                                                            "muc": "c",
                                                            "requirement_name": "Tối ưu cấu hình và chính sách an ninh mạng trên thiết bị",
                                                            "description": [
                                                                {{
                                                                    "description_detail": "Rà soát các cấu hình và chính sách an ninh mạng được thiết lập trên thiết bị."
                                                                }}
                                                            ]
                                                        }}
                                                    }}
                                                ]
                                            }}
                                        }}
                                    ]
                                }}
                            }}
                        ]
                    }}

            ]
            ví dụ 2: 
            OUTPUT NHƯ SAU:
            {{	"hr": [             
                    ]
            }},
            {{
                "requirement_level_0": {{
                    "muc": "1.",
                    "requirement_name": "Yêu cầu về kỹ thuật",
                    "sub_requirements": [
                        {{
                            "requirement_level_1": {{
                                "muc": "1.2.",
                                "requirement_name": "Yêu cầu về kỹ thuật",
                                "sub_requirements": [
                                    {{
                                        "requirement_level_2": {{
                                            "muc": "1",
                                            "requirement_name": "Bản quyền phần mềm Microsoft Office LTSC Standard 2021",
                                            "description": [
                                                {{
                                                    "description_detail": "Đảm bảo tương thích với hệ điều hành Windows 10, Windows 11"
                                                }},
                                                {{
                                                    "description_detail": "Bao gồm các ứng dụng cơ bản như Word, Excel, PowerPoint và Outlook."
                                                }}
                                            ]
                                        }}
                                    }}
                                ]
                            }},
                            "requirement_level_1": {{
                                "muc": "1.3.",
                                "requirement_name": "Các yêu cầu khác",
                                "sub_requirements": [
                                    {{
                                        "requirement_level_2": {{
                                            "muc": "1.3.1",
                                            "requirement_name": "Yêu cầu về Bản quyền",
                                            "description": [
                                                {{
                                                    "description_detail": "- Hàng hóa cung cấp mới 100% chưa qua sử dụng"
                                                }},
                                                {{
                                                    "description_detail": "- Có Giấy phép hoặc giấy ủy quyền bán hàng của nhà sản xuất, đại lý phân phối hoặc giấy chứng nhận quan hệ đối tác hoặc tài liệu khác có giá trị tương đương."
                                                }}
                                            ]
                                        }}
                                    }},
                                    {{
                                        "requirement_level_2": {{
                                            "muc": "1.3.2",
                                            "requirement_name": "Yêu cầu về bảo hành, hỗ trợ kỹ thuật",
                                            "description": [
                                                {{
                                                    "description_detail": "Nhà thầu phải có văn phòng hoặc cơ sở tại Hà Nội "
                                                }},
                                            ]
                                        }}
                                    }}
                                ]
                            }}
                        }}
                    ]
                }}
            }}

            ví dụ 3:
                
                {{	"hr": [
                        {{
                            "position": "Trưởng nhóm triển khai",
                            "quantity": "1",
                            "requirements": [
                                {{
                                    "name": "",
                                    "description": "- Tối thiểu 03 năm hoặc tối thiểu 01 hợp đồng."
                                }},
                                {{
                                    "name": "",
                                    "description": "- Tốt nghiệp Đại học chuyên ngành Công nghệ thông tin, An toàn thông tin hoặc Điện tử viễn thông, Điện tử truyền thông."
                                }},
                                {{
                                    "name": "",
                                    "description": "- Có chứng nhận hoặc chứng chỉ chứng minh đã được đào tạo về sản phẩm chào thầu"
                                }}					
                            ]                
                        }}
                    ]
                }},
                {{  "requirement_level_0": {{
                    "muc": "1.",
                    {{
                        "requirement_name": "Yêu cầu về kỹ thuật",
                        "sub_requirements": [
                            {{
                                "requirement_level_1": {{
                                    "muc": "1.2.",
                                    "requirement_name": "Yêu cầu về kỹ thuật",
                                    "sub_requirements": [
                                        {{
                                            "requirement_level_2": {{
                                                "muc": "1",
                                                "requirement_name": "Bản quyền phần mềm Microsoft Office LTSC Standard 2021",
                                                "description": [
                                                    {{
                                                        "description_detail": "Đảm bảo tương thích với hệ điều hành Windows 10, Windows 11"
                                                    }},
                                                    {{
                                                        "description_detail": "Bao gồm các ứng dụng cơ bản như Word, Excel, PowerPoint và Outlook."
                                                    }}
                                                ]
                                            }}
                                        }}
                                    ]
                                }}
                            }}
                        ]
                    }}
                }}
            }}
            Return only the JSON in this format:
                    
            [
                {{"hr": [
                        {{
                            "position": "Vị trí công việc, nếu không có yêu cầu bắt buộc để giá trị rỗng",
                            "quantity": "Số lượng yêu cầu, nếu không có yêu cầu bắt buộc để giá trị 0",
                            "requirements": [
                                {{
                                    "name": "tên yêu cầu, nếu không có yêu cầu bắt buộc để giá trị rỗng",
                                    "description": "mô tả chi tiết của yêu cầu, nếu không có yêu cầu bắt buộc để giá trị rỗng"
                                }}
                            ]                
                        }}
                    ]
                }},	
                {{
                    "requirement_level_0": {{
                        "muc": "số chỉ mục",
                        "requirement_name": "Yêu cầu kỹ thuật",
                        "sub_requirements": [
                            {{
                                "requirement_level_1": {{
                                    "muc": "số chỉ mục",
                                    "requirement_name": "tên yêu cầu là các yêu cầu trong phạm vi mô tả ở trên có level nhỏ hơn level 0",
                                    "sub_requirements": [
                                        {{
                                            "requirement_level_2": {{
                                                "muc": "số chỉ mục",
                                                "requirement_name": "tên yêu cầu là các yêu cầu có level nhỏ hơn level 1",
                                                "sub_requirements": [
                                                    {{
                                                        "requirement_level_3": {{
                                                            "requirement_name": "tên yêu cầu là các yêu cầu có level nhỏ hơn level 2",
                                                            "description": [
                                                                {{
                                                                    "description_detail": "mô tả từng chi tiết của yêu cầu"
                                                                }}
                                                            ]
                                                        }}
                                                    }}
                                                ]
                                            }}
                                        }}
                                    ]
                                }}
                            }}
                        ]
                    }}
                }}
            ]                                       
                        
            Nội dung hồ sơ mời thầu:
                {content}
    """

    def _merge_technical_results(self, results):
        """Merge technical requirements from different chunks"""
        if not results:
            return []

        # Simple approach: if each chunk returns a list of requirements at level 0,
        # we can concatenate them
        merged = []

        for result in results:
            # Skip empty results
            if not result:
                continue

            # Handle different result structures
            if isinstance(result, list):
                merged.extend(result)
            elif isinstance(result, dict) and "requirement_level_0" in result:
                merged.append(result)

        return merged
