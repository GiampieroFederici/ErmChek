"""Icona di Windows: il bacillo del logo (assets/logo/ErmChek_bacillo.png, disegno non modificato) su una piastrella
bianca con angoli arrotondati, così si vede anche su un Desktop scuro. Scrive assets/logo/ErmChek_icona.ico."""
from pathlib import Path

from PIL import Image, ImageDraw

LOGO = Path(__file__).resolve().parent.parent / "assets" / "logo"
GRANDE = 1024
bacillo = Image.open(LOGO / "ErmChek_bacillo.png").convert("RGBA")
bacillo = bacillo.crop(bacillo.getbbox())
tela = Image.new("RGBA", (GRANDE, GRANDE), (0, 0, 0, 0))
ImageDraw.Draw(tela).rounded_rectangle([16, 16, GRANDE - 17, GRANDE - 17], radius=200, fill=(255, 255, 255, 255),
                                       outline=(203, 213, 209, 255), width=14)
lato = int(GRANDE * 0.78)
scala = lato / max(bacillo.size)
b = bacillo.resize((round(bacillo.width * scala), round(bacillo.height * scala)), Image.LANCZOS)
tela.alpha_composite(b, ((GRANDE - b.width) // 2, (GRANDE - b.height) // 2))
tela.save(LOGO / "ErmChek_icona.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
tela.resize((256, 256), Image.LANCZOS).save(LOGO / "ErmChek_icona_256.png")
print("ok")

# immagine di avvio dell'eseguibile (PyInstaller --splash): compare subito, prima che Python sia pronto
from PIL import ImageFont  # noqa: E402

logo = Image.open(LOGO / "ErmChek_logo.png").convert("RGBA")
logo = logo.resize((480, round(480 * logo.height / logo.width)), Image.LANCZOS)
avvio = Image.new("RGB", (640, 300), (255, 255, 255))
avvio.paste(logo, ((640 - logo.width) // 2, 50), logo)
carattere = ImageFont.truetype(str(LOGO.parent / "fonts" / "AtkinsonHyperlegible-Regular.ttf"), 22)
d = ImageDraw.Draw(avvio)
testo = "Avvio in corso... / Starting..."
d.text(((640 - d.textlength(testo, font=carattere)) / 2, 230), testo, fill=(82, 98, 93), font=carattere)
d.rectangle([0, 0, 639, 299], outline=(203, 213, 209), width=2)
avvio.save(LOGO / "ErmChek_avvio.png")
