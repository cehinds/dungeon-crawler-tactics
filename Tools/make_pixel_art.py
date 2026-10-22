"""Generate original 32px pixel characters, exported at 128px for both clients.

This is an editable art source, not a dependency of the shipped game.
Install Pillow to regenerate. Shapes use integer pixels and a shared palette.
"""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / 'UnityPackage/Runtime/Resources/Art'
OUT.mkdir(parents=True, exist_ok=True)
INK = '#161b2a'
SKIN = '#e6b68e'
SKIN_SHADE = '#b77862'
STEEL = '#c6d9da'
GOLD = '#edc77d'

PALETTES = {
    'brawler': ('#bb704f', '#753c39', '#e3a676'),
    'guardian': ('#638b9c', '#374e6c', '#a6c8c5'),
    'rogue': ('#6e668c', '#39334f', '#ae97b6'),
    'ranger': ('#6f9b75', '#385849', '#b6c88c'),
    'pyromancer': ('#b86148', '#692f3d', '#e7a15e'),
    'cryomancer': ('#6ba5b9', '#395378', '#b9e0dc'),
    'stormcaller': ('#a08bc0', '#504869', '#d5b5d9'),
    'cleric': ('#c4be9f', '#777b82', '#f5e3b0'),
    'alchemist': ('#78a489', '#345c60', '#bfd488'),
    'bard': ('#bb8394', '#683f67', '#e8bda5'),
    'necromancer': ('#857f9d', '#37374d', '#afc5a8'),
    'beastmaster': ('#a68b56', '#5c573d', '#dbbc76'),
    'enemy': ('#a35d65', '#592f47', '#d59186'),
    'boss': ('#835d6f', '#422c48', '#c5928e'),
}


def character(kind):
    image = Image.new('RGBA', (32, 32))
    d = ImageDraw.Draw(image)
    main, dark, light = PALETTES[kind]
    d.ellipse((5, 27, 27, 30), fill=(8, 12, 24, 90))
    # Boots, dark outline, body, right-side shade.
    d.rectangle((10, 23, 14, 28), fill=INK)
    d.rectangle((18, 23, 22, 28), fill=INK)
    d.rectangle((9, 27, 14, 29), fill=INK)
    d.rectangle((18, 27, 23, 29), fill=INK)
    d.rectangle((10, 25, 13, 27), fill='#795653')
    d.rectangle((19, 25, 22, 27), fill='#795653')
    d.polygon([(10, 14), (22, 14), (25, 23), (20, 26), (12, 26), (7, 23)], fill=INK)
    d.polygon([(11, 15), (21, 15), (23, 23), (20, 24), (12, 24), (9, 23)], fill=main)
    d.rectangle((19, 16, 21, 23), fill=dark)
    d.rectangle((11, 16, 12, 21), fill=light)
    d.rectangle((10, 22, 22, 23), fill=dark)
    d.rectangle((15, 22, 17, 23), fill=GOLD)
    # Arms and cuffs.
    d.rectangle((6, 16, 9, 22), fill=INK)
    d.rectangle((7, 17, 9, 20), fill=main)
    d.rectangle((7, 21, 9, 23), fill=SKIN_SHADE)
    d.rectangle((23, 16, 26, 22), fill=INK)
    d.rectangle((23, 17, 25, 20), fill=dark)
    d.rectangle((23, 21, 25, 23), fill=SKIN)
    # Head, hair and readable eyes.
    d.rectangle((10, 5, 22, 13), fill=INK)
    d.rectangle((12, 4, 20, 14), fill=INK)
    d.rectangle((11, 6, 21, 12), fill=SKIN_SHADE)
    d.rectangle((12, 6, 20, 12), fill=SKIN)
    d.rectangle((13, 13, 19, 14), fill=SKIN)
    d.rectangle((11, 5, 21, 7), fill='#62473f')
    d.rectangle((12, 4, 19, 5), fill='#8a6350')
    d.point((13, 10), fill=INK)
    d.point((19, 10), fill=INK)
    d.rectangle((15, 12, 17, 12), fill=SKIN_SHADE)
    if kind == 'brawler':
        d.rectangle((12, 17, 20, 21), fill=SKIN)
        d.rectangle((12, 17, 13, 20), fill=SKIN_SHADE)
        d.rectangle((5, 19, 9, 23), fill=SKIN)
        d.rectangle((23, 19, 27, 23), fill=SKIN)
        d.rectangle((10, 26, 13, 28), fill=SKIN)
        d.rectangle((19, 26, 22, 28), fill=SKIN)
        d.rectangle((14, 13, 18, 14), fill='#704c44')
    elif kind in ('guardian', 'boss'):
        d.rectangle((10, 4, 22, 9), fill=dark)
        d.rectangle((11, 4, 21, 5), fill=STEEL)
        d.rectangle((15, 3, 17, 8), fill=light)
        d.polygon([(3, 17), (10, 16), (11, 24), (7, 27), (3, 24)], fill=INK)
        d.polygon([(4, 18), (9, 17), (10, 23), (7, 25), (4, 23)], fill=main)
        d.line((7, 18, 7, 24), fill=GOLD)
        d.rectangle((25, 8, 26, 23), fill=INK)
        d.rectangle((25, 9, 25, 19), fill=STEEL)
        d.rectangle((23, 20, 28, 21), fill=GOLD)
        if kind == 'boss':
            d.polygon([(10, 5), (6, 1), (8, 8)], fill=GOLD)
            d.polygon([(22, 5), (26, 1), (24, 8)], fill=GOLD)
    elif kind in ('rogue', 'ranger', 'necromancer'):
        d.polygon([(9, 9), (10, 4), (16, 1), (22, 4), (23, 9), (20, 7), (12, 7)], fill=dark)
        d.line((11, 5, 16, 2, 21, 5), fill=light, width=1)
        d.rectangle((12, 12, 20, 13), fill=main)
        if kind == 'ranger':
            d.line((26, 10, 29, 14, 29, 22, 26, 26), fill=GOLD, width=1)
            d.line((26, 10, 26, 26), fill=STEEL)
        elif kind == 'rogue':
            d.line((25, 13, 25, 22), fill=STEEL, width=2)
            d.rectangle((23, 22, 27, 22), fill=GOLD)
        else:
            d.rectangle((25, 12, 26, 28), fill='#796c72')
            d.ellipse((22, 7, 28, 13), fill='#c9d4b8')
            d.point((24, 10), fill=INK)
            d.point((27, 10), fill=INK)
    elif kind in ('pyromancer', 'cryomancer', 'stormcaller', 'cleric'):
        d.polygon([(10, 5), (15, 0), (19, 3), (22, 6)], fill=dark)
        d.rectangle((9, 6, 23, 7), fill=main)
        d.rectangle((10, 24, 22, 27), fill=dark)
        d.rectangle((12, 24, 13, 26), fill=light)
        d.rectangle((26, 11, 27, 28), fill='#956b54')
        d.rectangle((25, 13, 28, 14), fill=GOLD)
        gem = {'pyromancer':'#f6ab59','cryomancer':'#a1ebed','stormcaller':'#d9a4ed','cleric':'#fff0c5'}[kind]
        d.polygon([(26, 6), (29, 9), (27, 12), (24, 9)], fill=dark)
        d.polygon([(26, 7), (28, 9), (27, 11), (25, 9)], fill=gem)
        d.point((26, 8), fill='#ffffff')
    elif kind == 'alchemist':
        d.rectangle((11, 8, 21, 10), fill=INK)
        d.rectangle((12, 8, 14, 10), fill='#a4d9ba')
        d.rectangle((18, 8, 20, 10), fill='#a4d9ba')
        d.rectangle((25, 17, 26, 19), fill=STEEL)
        d.ellipse((23, 20, 28, 25), fill='#568d69')
        d.rectangle((24, 21, 27, 23), fill='#b6e5a0')
        d.point((24, 21), fill='#efffeb')
    elif kind == 'bard':
        d.ellipse((21, 17, 28, 25), fill=GOLD)
        d.rectangle((25, 11, 26, 21), fill='#875c47')
        d.ellipse((23, 20, 25, 22), fill=dark)
        d.polygon([(17, 4), (22, 0), (23, 3), (19, 6)], fill=light)
    elif kind == 'beastmaster':
        d.rectangle((9, 14, 23, 16), fill='#ccb980')
        d.rectangle((11, 15, 12, 17), fill='#f1dc9f')
        d.rectangle((20, 15, 21, 17), fill='#f1dc9f')
        d.rectangle((26, 7, 27, 27), fill='#b4a27b')
        d.polygon([(25, 7), (27, 3), (29, 7)], fill=STEEL)
    elif kind == 'enemy':
        d.rectangle((12, 8, 20, 12), fill='#a6af89')
        d.point((13, 10), fill='#ffdb8a')
        d.point((19, 10), fill='#ffdb8a')
        d.polygon([(10, 8), (6, 6), (9, 11)], fill='#a6af89')
        d.polygon([(22, 8), (26, 6), (23, 11)], fill='#a6af89')
        d.rectangle((25, 15, 27, 24), fill='#89726a')
        d.rectangle((23, 12, 29, 17), fill=STEEL)
    return image


def donut():
    im = Image.new('RGBA', (32, 32))
    d = ImageDraw.Draw(im)
    d.ellipse((4, 27, 28, 30), fill=(8, 12, 24, 90))
    d.line((23, 25, 28, 23, 29, 18, 27, 16), fill=INK, width=4)
    d.line((23, 25, 28, 23, 29, 18, 27, 16), fill='#bf9c79', width=2)
    d.polygon([(8, 15), (23, 15), (25, 26), (21, 29), (9, 29), (6, 26)], fill=INK)
    d.polygon([(9, 16), (22, 16), (24, 26), (20, 27), (9, 27), (7, 26)], fill='#997ab4')
    d.rectangle((10, 23, 13, 28), fill='#e1c29d')
    d.rectangle((18, 23, 21, 28), fill='#e1c29d')
    d.rectangle((14, 18, 17, 24), fill='#d7bfda')
    d.rectangle((8, 7, 23, 17), fill=INK)
    d.polygon([(9, 10), (7, 3), (13, 7), (19, 7), (24, 3), (23, 12)], fill=INK)
    d.polygon([(10, 10), (9, 5), (14, 8), (19, 8), (22, 5), (22, 12)], fill='#bf9c79')
    d.rectangle((9, 9, 22, 16), fill='#dabb93')
    d.rectangle((11, 13, 20, 17), fill='#eddbb6')
    d.rectangle((11, 11, 13, 12), fill='#5c8b8a')
    d.rectangle((18, 11, 20, 12), fill='#5c8b8a')
    d.point((12, 11), fill=INK)
    d.point((19, 11), fill=INK)
    d.rectangle((15, 14, 16, 14), fill='#b87986')
    d.point((16, 15), fill=INK)
    d.line((6, 13, 10, 14), fill=STEEL)
    d.line((21, 14, 26, 13), fill=STEEL)
    d.polygon([(11, 7), (10, 2), (14, 4), (16, 1), (18, 4), (22, 2), (21, 7)], fill=GOLD)
    d.point((16, 4), fill='#9a6aaf')
    return im


if __name__ == '__main__':
    pictures = {name: character(name) for name in PALETTES}
    pictures['donut'] = donut()
    for name, picture in pictures.items():
        picture.resize((128, 128), Image.Resampling.NEAREST).save(OUT / (name + '.png'))
    sheet = Image.new('RGBA', (5 * 128, 3 * 128), '#1b2432')
    for index, picture in enumerate(pictures.values()):
        sheet.alpha_composite(picture.resize((128, 128), Image.Resampling.NEAREST), ((index % 5)*128, (index//5)*128))
    sheet.save(OUT / 'contact-sheet.png')
    print(f'Wrote {len(pictures)} original 128px sprites and contact sheet to {OUT}')
