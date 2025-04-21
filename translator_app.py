import tkinter as tk
from tkinter import scrolledtext, font
import os
from dotenv import load_dotenv
from LLMClient import LLMClient
import re  # 导入 re 模块用于解析


class TranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("npy话语解读器")
        self.root.geometry("700x650")  # 稍微增加高度以容纳按钮

        # --- LLMClient 初始化部分 (保持不变) ---
        self.llm_client = None
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                print("错误：OPENAI_API_KEY 环境变量未设置。")
                # 在实际应用中，可能需要更好的错误处理，比如弹出对话框
                # exit(1) # 不直接退出，允许界面启动但功能受限
            base_url = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
            model = os.getenv("OPENAI_DEFAULT_MODEL", "deepseek/deepseek-chat-v3-0324:free")
            # 只有在 api_key 有效时才尝试初始化
            if api_key:
                self.llm_client = LLMClient(api_key=api_key, base_url=base_url, model=model)
            else:
                print("警告：API Key 未设置，LLM 功能将不可用。")

        except Exception as e:
            print(f"初始化 LLMClient 时出错: {e}")
            # 可以在界面上显示错误信息
        # --- 界面布局代码 ---
        main_frame = tk.Frame(root, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        # 调整行权重，为回复区预留空间
        main_frame.rowconfigure(1, weight=1)  # 输入/解读文本区
        main_frame.rowconfigure(3, weight=0)  # 回复按钮区 (不扩展)

        # 定义统一的字体
        f = font.families()
        self.default_font = font.Font(family="song ti", size=20)
        self.button_font = font.Font(family="song ti", size=16)

        input_label = tk.Label(main_frame, text="输入她的话：", font=self.default_font)
        input_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))

        self.input_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, width=40,  # 调整高度
                                                    font=self.default_font)
        self.input_text.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        result_label = tk.Label(main_frame, text="解读：", font=self.default_font)
        result_label.grid(row=0, column=1, sticky=tk.W, pady=(0, 5))

        self.result_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15, width=40, state=tk.DISABLED,
                                                     # 调整高度
                                                     font=self.default_font)
        self.result_text.grid(row=1, column=1, sticky="nsew", padx=(10, 0))

        translate_button = tk.Button(main_frame, text="解读", command=self.translate_text,
                                     font=self.button_font)  # 使用按钮字体
        translate_button.grid(row=2, column=0, columnspan=2, pady=(15, 10))  # 调整按钮位置和边距

        # --- 新增：用于显示建议回复的 Frame ---
        replies_label = tk.Label(main_frame, text="建议回复：", font=self.default_font)
        replies_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(10, 5))

        self.replies_frame = tk.Frame(main_frame)
        self.replies_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        self.replies_frame.columnconfigure(0, weight=1)  # 让标签占据主要宽度

        # --- 状态标签，用于显示复制成功等信息 ---
        self.status_label = tk.Label(main_frame, text="", font=self.button_font, fg="green")
        self.status_label.grid(row=5, column=0, columnspan=2, pady=(5, 0))

    def display_error(self, message):
        """辅助函数，用于在结果框中显示错误信息"""
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, f"错误：\n{message}")
        self.result_text.config(state=tk.DISABLED)
        # 清空建议回复区域
        self._clear_replies_frame()
        self.show_status("")  # 清除状态信息

    def _clear_replies_frame(self):
        """清空建议回复区域的辅助函数"""
        for widget in self.replies_frame.winfo_children():
            widget.destroy()

    def show_status(self, message, duration=2000):
        """显示状态信息，并在一段时间后自动清除"""
        self.status_label.config(text=message)
        if duration:
            self.root.after(duration, lambda: self.status_label.config(text=""))

    def translate_text(self):
        input_content = self.input_text.get("1.0", tk.END).strip()
        if not input_content:
            self.display_error("请输入内容后再解读。")
            return

        if not self.llm_client:
            self.display_error("LLM 服务未初始化 (请检查 API Key)。")
            return

        # 更新UI，准备接收流式响应
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert(tk.END, "正在思考中...\n")
        self.result_text.config(state=tk.DISABLED)
        self._clear_replies_frame()  # 清空旧的回复建议
        self.show_status("")  # 清空状态栏
        self.root.update_idletasks()

        # **** COSTAR 框架系统提示词 (保持不变) ****
        system_prompt = """
## Context
你正在帮助一位用户解读他伴侣（女朋友或媳妇）所说的一句话。用户希望了解这句话表面之下的潜在含义，例如潜台词、反语、未明说的期望或真实的情感。输入的语句会由用户提供。请注意，你可能不了解具体的对话背景和双方关系细节，需要基于对人际交往和亲密关系的普遍理解进行分析。

## Objective
你的目标是：
1. 分析用户提供的语句。
2. 解读其最可能的真实含义，识别任何潜在的潜台词、反语或隐藏的情感。并用一句话表达ta想表达的意思。
3. 提供一个清晰、有洞察力的解释。
4. **重要:** 在解释之后，另起一行，使用 "可能的回复:" 开头，然后按编号列出3条建议的回复，每条不超过20字。格式如下：
可能的回复:
1. 回复一示例
2. 回复二示例
3. 回复三示例

## Style
请以一位情商高、富有同理心和洞察力的朋友或情感顾问的风格来回应。你的语言应该易于理解且具有建设性。

## Tone
保持理解、客观和支持性的语气。避免指责或评判任何一方。专注于提供有帮助的解读。

## Audience
回应的对象是寻求理解伴侣真实想法的用户。

## Response Format
请严格按照以下格式组织你的回应：
使用翻译的方式用一句话简要写出表达ta想表达的意思。
并将其放在''内
然后另起新行，使用 \'可能的回复:\' 作为明确的标记。
接着按编号（1., 2., 3.）列出三条回复建议，每条占一行，且不超过20字。
例如：
‘想你了’
可能的回复:
1. 我知道了，抱抱你。
2. 是我没考虑周全，下次注意。
3. 那我们聊聊这个？

请不要使用 markdown 语法。
请直接开始你的解读，无需重复本提示词内容。
"""
        user_prompt = f"请解读这句话：\"{input_content}\""

        full_response_text = ""  # 用于累积完整响应
        try:
            # 调用 LLMClient 的 completion 方法获取流式响应迭代器
            response_stream = self.llm_client.completion(
                system_prompt=system_prompt,
                user_message=user_prompt,
                temperature=0.7,
                max_tokens=300
            )

            # 首次接收前清空"正在思考"
            first_chunk = True
            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete("1.0", tk.END)  # 清空"正在思考"

            # 迭代处理流式响应
            for chunk in response_stream:
                # 检查是否是错误信息 (根据 LLMClient 中 yield 的错误格式)
                if isinstance(chunk, str) and chunk.startswith("\n[错误："):
                    self.display_error(chunk.strip())  # 使用 display_error 显示错误
                    return  # 出错则停止处理

                if first_chunk:
                    # self.result_text.delete("1.0", tk.END) # 已经在循环外清空
                    first_chunk = False

                # 实时显示在主结果框 (但处理完成后会重新整理)
                self.result_text.insert(tk.END, chunk)
                self.result_text.see(tk.END)
                self.root.update_idletasks()

                full_response_text += chunk  # 累积完整文本

            # --- 流处理完毕后，解析并重新布局 ---
            self.result_text.config(state=tk.NORMAL)
            self.result_text.delete("1.0", tk.END)  # 清空临时显示的内容

            # 解析回复
            interpretation = full_response_text
            replies = []
            reply_section_match = re.search(r"可能的回复:\s*\n((?:^\d+\.\s*.*$\n?)+)", full_response_text,
                                            re.MULTILINE | re.IGNORECASE)

            if reply_section_match:
                interpretation = full_response_text[:reply_section_match.start()].strip()
                reply_lines = reply_section_match.group(1).strip().split('\n')
                for line in reply_lines:
                    match = re.match(r"^\d+\.\s*(.*)", line.strip())
                    if match:
                        replies.append(match.group(1).strip())

            # 显示解读部分
            self.result_text.insert(tk.END, interpretation if interpretation else "未能提取解读内容。")
            self.result_text.config(state=tk.DISABLED)

            # 显示建议回复和按钮
            self._clear_replies_frame()  # 再次确保清空
            if replies:  # 回复按钮小一点
                for i, reply_text in enumerate(replies):
                    # 使用 lambda 捕获当前的 reply_text 值
                    copy_cmd = lambda text=reply_text: self.copy_to_clipboard(text)

                    reply_label = tk.Label(self.replies_frame, text=f"{i + 1}. {reply_text}", anchor="w",
                                           justify=tk.LEFT, font=self.default_font)
                    reply_label.grid(row=i, column=0, sticky="ew", pady=2, padx=(0, 5))

                    copy_button = tk.Button(self.replies_frame, text="复制", command=copy_cmd, font=self.button_font)
                    copy_button.grid(row=i, column=1, sticky="e", pady=2, padx=(5, 0))
            else:
                no_reply_label = tk.Label(self.replies_frame, text="未能提取建议回复。", font=self.button_font, fg="gray")
                no_reply_label.grid(row=0, column=0, columnspan=2)


        except Exception as e:
            self.display_error(f"处理响应时发生意外错误：{e}")
            # 确保文本框最终是禁用的
            if self.result_text:
                self.result_text.config(state=tk.DISABLED)

    def copy_to_clipboard(self, text_to_copy):
        """将文本复制到剪贴板"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
            print(f"已复制: {text_to_copy}")  # 控制台输出提示
            self.show_status(f"已复制: \"{text_to_copy[:20]}{'...' if len(text_to_copy) > 20 else ''}\"")  # 界面状态提示
        except Exception as e:
            print(f"复制到剪贴板时出错: {e}")
            self.show_status("复制失败", duration=3000)


# --- 主程序入口 (保持不变) ---
if __name__ == "__main__":
    load_dotenv()  # 加载 .env 文件
    root = tk.Tk()
    app = TranslatorApp(root)
    root.mainloop()
