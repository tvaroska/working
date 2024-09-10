"""

    Tests for agentic UI

"""
import asyncio
import flet as ft

async def main(page: ft.Page):

    async def on_start(e: ft.ControlEvent):
        upload_button.disabled = True
        progress_ring.visible = True
        progress_text.visible = True
        e.page.update()
        e.page.run_task(update)

    async def update():
        counter = 1
        while counter <= 10:
            await asyncio.sleep(1)
            progress_text.value = f"Counter {counter}"
            progress_text.update()
            counter += 1

        progress_ring.value = 1
        page.update()

    upload_button = ft.ElevatedButton(
                'Start counting',
                icon=ft.icons.START,
                on_click=on_start
            )

    progress_ring = ft.ProgressRing(height=20, width=20)
    progress_ring.visible = False

    progress_text = ft.Text('Counter is to 0')
    progress_text.visible = False

    top_row = ft.Row(
        controls = [
            upload_button,
            progress_ring,
            progress_text
            ]
    )

    bottom_row = ft.Row(
        controls = [ft.Text('Bottom')]
    )

    page.add(
        top_row,
        ft.Divider(),
        bottom_row)

ft.app(main)
