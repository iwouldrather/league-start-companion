"""Rasterize our original compass mark into Windows' multi-size ICO format."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]

def main():
    scale=4
    image=Image.new('RGBA',(256*scale,256*scale))
    draw=ImageDraw.Draw(image)
    def points(values):return [(x*scale,y*scale) for x,y in values]
    draw.rounded_rectangle((16,16,1008,1008),radius=220,fill='#101d2c')
    diamond=points([(128,29),(227,128),(128,227),(29,128)])
    draw.polygon(diamond,fill='#172c3d')
    draw.line(diamond+[diamond[0]],fill='#d9b976',width=9*scale,joint='curve')
    draw.polygon(points([(128,57),(156,128),(128,199),(100,128)]),fill='#79cfee')
    draw.polygon(points([(128,57),(128,128),(156,128)]),fill='#c2efff')
    draw.polygon(points([(128,128),(128,199),(100,128)]),fill='#386d94')
    for x,y,r,fill,outline in [(128,128,16,'#101d2c','#d9b976'),(54,128,9,'#d9b976',None),(202,128,9,'#d9b976',None)]:
        draw.ellipse(((x-r)*scale,(y-r)*scale,(x+r)*scale,(y+r)*scale),fill=fill,outline=outline,width=7*scale if outline else 1)
    image=image.resize((256,256),Image.Resampling.LANCZOS)
    image.save(ROOT/'assets/app-icon.png')
    image.save(ROOT/'assets/app-icon.ico',sizes=[(s,s) for s in (16,24,32,48,64,128,256)])

if __name__=='__main__':main()
