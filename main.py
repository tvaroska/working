"""

    Sample to show Gemini with caching to execute agentic reflection
    User upload PDF - gemini create summarization

"""
import os
import flet as ft

from vertexai.generative_models import GenerativeModel, Part

async def main(page: ft.Page):

    model = GenerativeModel(model_name="gemini-1.5-pro-001")

    async def get_file(e: ft.FilePickerResultEvent):
        if e.files:
            progress_ring.visible = True
            progree_text.visible = True
            file = e.files[0]

            upload_file = ft.FilePickerUploadFile(
                file.name,
                upload_url=e.page.get_upload_url(file.name, 60)
            )

            pick_file_dialog.upload([upload_file])

            text_part = Part.from_text("Summarize content of attached paper into three paragraphs")
            with open(f"/tmp/flet/{file.name}", "rb") as f:
                data = f.read()
            pdf_part = Part.from_data(data, "application/pdf")
            response = model.generate_content(contents=[text_part, pdf_part])
            model_response.value = response.candidates[0].content.parts[0].text
        else:
            model_response.value = "Cancelled!"
        model_response.update()

    page.title = "Gemini Reflection sample"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    # example for generating page theme colors based on the seed color
    page.theme = ft.Theme(color_scheme_seed="blue")

    pick_file_dialog = ft.FilePicker(on_result=get_file)
    pick_file_button = ft.ElevatedButton(
                    text="Select PDF File",
                    icon=ft.icons.UPLOAD_FILE,
                    on_click=lambda _: pick_file_dialog.pick_files(
                        allow_multiple=True
                    ),
                )

    progress_ring = ft.ProgressRing(width=20, height=20, visible=False)
    progree_text = ft.Text("Processing", visible=False)

    file_column = ft.Column(
            alignment=ft.alignment.top_left,
            controls=[
                pick_file_button,
                ft.Row(controls = [progress_ring, progree_text])

            ]
        )

    file_container = ft.Container(
        height=page.height,
        width=200,
        content=file_column
    )

    model_response = ft.Text("Response will be here")
    page.overlay.append(pick_file_dialog)

    page.add(
        ft.AppBar(
            title=ft.Text("Gemini Reflection samples"),
            center_title=True,
            # TODO: reset button
#             actions=[pick_file_button]
        ),
        ft.ResponsiveRow(
            [
                ft.Column(
                    col=2,
                    controls=[file_container]),
                ft.Column(col=1, controls=[ft.VerticalDivider()]),
                ft.Column(col=9, controls=[model_response])
            ]
        )
    )

os.environ["FLET_SECRET_KEY"] = "SECRET_KEY"
ft.app(main, upload_dir="/tmp/flet", view=ft.AppView.WEB_BROWSER)
