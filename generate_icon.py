"""Utilitário para gerar o ícone nativo .ico de alta resolução do BROWSER MTS.

Gera o arquivo de ícone em múltiplas resoluções padrão do Windows (16x16 a 256x256)
para compilação com PyInstaller e inclusão no instalador Inno Setup.
"""

from PIL import Image, ImageDraw


def generate_app_icon(output_path: str = "app_icon.ico") -> None:
    """Gera um arquivo de ícone Windows (.ico) multi-camadas."""
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    images = []

    for width, height in sizes:
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Círculo externo com fundo escuro Fluent
        padding = max(1, width // 16)
        draw.ellipse([padding, padding, width - padding, height - padding], fill="#1E1E1E", outline="#0078D4", width=max(1, width // 24))

        # Anel interno de destaque (Teal / Cyan)
        ring_pad = max(2, width // 6)
        draw.ellipse([ring_pad, ring_pad, width - ring_pad, height - ring_pad], fill="#0F2D3D", outline="#00A4EF", width=max(1, width // 32))

        # Ponto / LED central de conectividade
        center_pad = max(3, width // 3)
        draw.ellipse([center_pad, center_pad, width - center_pad, height - center_pad], fill="#107C41")

        images.append(img)

    # Salva o arquivo .ico com todas as resoluções embutidas
    images[0].save(output_path, format="ICO", sizes=[(im.width, im.height) for im in images])
    print(f"Ícone gerado com sucesso em: {output_path}")


if __name__ == "__main__":
    generate_app_icon()

