"""Draw the unformed alloy furnace controller and its inventory panel."""

NS = "expedition_industry"


def panel_image(kind):
    from PIL import Image, ImageDraw

    picture = Image.new("RGBA", (16,16))
    d = ImageDraw.Draw(picture)
    if kind == "keys":
        d.rectangle((0,0,15,15),fill="#707771")
        d.rectangle((1,3,14,12),fill="#424b4a")
        for x in (3,5,7,9,11):
            for y in (4,7,10):
                d.point((x,y),fill="#a1a6a0")
        d.line((6,11,10,11),fill="#b5b8ac")
    elif kind == "case":
        d.rectangle((0,0,15,15), fill="#6c7472")
        d.line((0,0,15,0), fill="#a4a99a")
        d.line((0,15,15,15), fill="#454e50")
        d.line((1,4,1,12), fill="#868d83")
        for x in (2,13):
            d.point((x,2), fill="#c7ba96")
            d.point((x,13), fill="#3b4344")
    elif kind == "ports":
        picture = panel_image("case")
        d = ImageDraw.Draw(picture)
        d.rectangle((2,6,13,11), fill="#39464a")
        d.rectangle((3,8,4,9), outline="#b9c9c3")
        d.line((6,10,7,7), fill="#dfb36b")
        for x, lamp in ((9,"#69b9b2"),(12,"#dfb36b")):
            d.point((x,8), fill=lamp)
            d.point((x,9), fill="#97634c")
    return picture


def console_screen(state, frame=None):
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (16,16), "#131d20")
    d = ImageDraw.Draw(img)
    d.rectangle((3,2,12,7), fill="#233238")
    d.line((3,2,12,2), fill="#4b6566")
    d.line((3,7,12,7), fill="#384b4e")
    if frame is not None:
        d.line((4,6,11,6), fill="#a36b41")
        for x in range(4,12):
            height = 1 + ((x*3 + frame + (x//2)*frame) % 4)
            d.line((x,6-height,x,6), fill="#e1904d" if height > 2 else "#c07242")
            if height > 2:
                d.point((x,6-height), fill="#f4bf76")
    else:
        d.line((4,6,8,6), fill="#4b6664")
    d.point((11,6), fill={"base":"#926853","ready":"#8cc687","working":"#a8cc80",
                          "waiting":"#f6bd67","suspend":"#827d6c"}[state])
    return img


def console_model(elt):
    tilt = {"origin": [8,9,8], "axis": "x", "angle": 22.5}
    def frame(lo, hi, faces):
        return elt(lo, hi, faces, rotation=tilt)
    side = "#case"
    return {"parent": "minecraft:block/block",
            "textures": {
                "particle": f"{NS}:block/works/alloy_case", "case": f"{NS}:block/works/alloy_case",
                "keys": f"{NS}:block/works/alloy_keys", "ports": f"{NS}:block/works/alloy_ports",
                "screen": f"{NS}:block/works/alloy_base"},
            "elements": [
                elt([0,0,0],[16,3,16],{"down":"#ports","up":"#keys","north":side,"south":"#ports","west":side,"east":side}),
                elt([4,3,9],[12,6,14],{"west":side,"east":side,"north":side,"south":side}),
                frame([1,5,5],[15,13,13],{"west":side,"east":side,"up":side,"down":side,"south":"#ports"}),
                frame([1,5,4],[15,6,5],{"north":side,"west":side,"east":side,"down":side}),
                frame([1,12,4],[15,13,5],{"north":side,"west":side,"east":side,"up":side}),
                frame([1,6,4],[3,12,5],{"north":side,"west":side,"east":side}),
                frame([13,6,4],[15,12,5],{"north":side,"west":side,"east":side}),
                frame([3,6,4],[13,6,5],{"up":side}),
                frame([3,12,4],[13,12,5],{"down":side}),
                elt([3,6,5],[13,12,5],{"north":"#screen"},rotation=tilt,uv={"north":[3,2,13,8]}),
            ]}


def add_gui_art(export):
    from PIL import Image, ImageDraw

    def texture(name, size, fill):
        image = Image.new("RGBA", size, fill)
        w,h = size
        draw = ImageDraw.Draw(image)
        return image, draw, w,h

    def save(name,image):
        export.png(NS,f"gui/works/alloy_{name}",image)

    def bevel(draw, box, light, dark, fill):
        x0,y0,x1,y1 = box
        draw.rectangle(box,fill=fill)
        draw.line((x0,y1,x0,y0,x1,y0),fill=light)
        draw.line((x0+1,y1,x1,y1,x1,y0+1),fill=dark)

    image,d,w,h = texture("case", (218,198), "#3f4748")
    bevel(d,(1,1,w-2,h-2),"#a6ada6","#2e3637","#707977")
    bevel(d,(4,4,w-5,h-5),"#7b8381","#4c5554","#646d6d")
    for x,y in ((4,4),(w-5,4),(4,h-5),(w-5,h-5)):
        d.point((x,y),fill="#c4c6ba")
    save("case",image)

    image,d,w,h = texture("screen", (202,105), "#3e4947")
    bevel(d,(1,1,w-2,h-2),"#303a3c","#adb2a7","#555f5c")
    bevel(d,(4,4,w-5,h-5),"#182222","#708078","#253433")
    d.line((7,7,w-8,7),fill="#3e514c")
    d.line((7,h-8,w-8,h-8),fill="#344745")
    save("screen",image)

    for name, stripe in (("item_input","#79a797"),("fluid_input","#6facad"),
                         ("item_output","#b4ac81"),("fluid_output","#aa9767")):
        image,d,w,h = texture(name,(18,18),"#273636")
        bevel(d,(0,0,w-1,h-1),"#445451","#7b8580","#192827")
        d.line((3,15,14,15),fill=stripe)
        save(name,image)

    for name, fill in (("process_empty","#374a44"),("process_fill","#83baa2")):
        image,d,_,_ = texture(name,(26,13),(0,0,0,0))
        d.polygon(((1,4),(17,4),(17,1),(24,6),(17,11),(17,8),(1,8)),fill=fill)
        save(name,image)

    for name, fill in (("energy_empty","#142321"),("energy_fill","#659c85")):
        image,d,w,h = texture(name,(126,12),"#374840")
        bevel(d,(0,0,w-1,h-1),"#253534","#66746c",fill)
        if name.endswith("fill"):
            for x in range(6,125,8):
                d.line((x,2,x,9),fill="#547f70")
        save(name,image)


def add_console_art(export):
    add_gui_art(export)
    for kind in ("case", "ports", "keys"):
        export.png(NS, f"block/works/alloy_{kind}", panel_image(kind))
