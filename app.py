import json

import flet as ft
from flet import View, Page

def create_detail_view(page: Page, item: dict):
    def handle_back(e):
        page.go('/')
        
    content = ft.Container(
        url=item['url'],
        content=ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        icon_color='#1a237e',
                        on_click=handle_back
                    ),
                    ft.Text('Back to list', color='#1a237e', size=16, weight=ft.FontWeight.BOLD)
                ],
                alignment=ft.MainAxisAlignment.START
            ),
            ft.Divider(color='#3949ab'),
            ft.Text(item['title'], size=24, weight=ft.FontWeight.BOLD, color='#1a237e'),
            ft.Container(
                content=ft.Markdown(
                    item['long'],
                    selectable=True,
                    extension_set="commonmark",
                    code_theme="atom-one-dark",
                    code_style=ft.TextStyle(
                        font_family="monospace",
                        size=14,
                    ),
                ),
                padding=ft.padding.all(10),
                bgcolor='white',
                border_radius=8,
                border=ft.border.all(1, '#e0e0e0'),
            )
        ],
        spacing=20
    ))
    
    return View(
        route=f'/detail/{item["title"]}',
        controls=[
            ft.Container(
                content=content,
                width=800,
                padding=ft.padding.all(20),
            )
        ],
        bgcolor='#f0f2f5',
        vertical_alignment=ft.MainAxisAlignment.START,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER
    )

async def main(page: ft.Page):

    with open('latest.json') as f:
        data = json.load(f)

    page.title = f'Weekly updates date: {data["date"]}'
    page.bgcolor = '#f0f2f5'  # Light gray background
    
    items = ft.ListView(width=800)
    
    # Create containers for list items
    for line in data["updates"]:
        container = ft.Container(
            on_click=lambda e: page.go(f'/detail/{e.control.content.controls[0].value}'),
            content=ft.Column(
                controls=[
                    ft.Text(line['title'], size=20, weight=ft.FontWeight.BOLD, color='#1a237e'),  # Dark blue
                    ft.Divider(color='#3949ab'),  # Lighter blue
                    ft.Text(line['short'], size=16, color='#37474f')  # Dark gray
                ],
                spacing=10
            ),
            border=ft.border.all(1, '#e0e0e0'),  # Light gray border
            border_radius=8,  # Rounded corners
            margin=ft.margin.all(2),
            padding=ft.padding.all(10),
            bgcolor='white',  # White background
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=4,
                color=ft.Colors.with_opacity(0.25, 'black'),
            ),
        )
        items.controls.append(container)

    # Initialize routing
    def route_change(e):
        page.views.clear()
        
        if page.route == "/":
            # Add main view
            page.views.append(
                View(
                    route='/',
                    controls=[items],
                    vertical_alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    bgcolor='#f0f2f5'
                )
            )
        else:
            # Add detail view
            for item in data["updates"]:
                if page.route == f'/detail/{item["title"]}':
                    page.views.append(create_detail_view(page, item))
                    break
        
        page.update()

    page.on_route_change = route_change


    # Center the list both horizontally and vertically
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    # Set initial route
    page.go('/')

ft.app(main, view=ft.WEB_BROWSER)
