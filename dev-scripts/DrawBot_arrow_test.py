from __future__ import division
from AppKit import NSColor, NSBezierPath, NSAffineTransform, NSString, NSFont, NSFontAttributeName, NSPoint, NSForegroundColorAttributeName, NSRect

def _drawArrow(position, kind, size, vector=(-1, 1), label_size=20):
        angle = atan2(vector[0], -vector[1])
        print vector, "%0.2f°" % degrees(angle)
        x, y = position
        head_ratio = 0.7
        w = size * 0.5
        tail_width = 0.3
        chin = 0.5 * (w - w * tail_width) # part under the head
        
        NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.9, 0.1, 0.0, 0.85 ).set()
        t = NSAffineTransform.transform()
        t.translateXBy_yBy_(x, y)
        t.rotateByRadians_(angle)
        myPath = NSBezierPath.alloc().init()
        
        myPath.moveToPoint_(         (0, 0)                                       )
        myPath.relativeLineToPoint_( (-size * head_ratio,        w * 0.5)         )
        myPath.relativeLineToPoint_( (0,                         -chin)           )
        myPath.relativeLineToPoint_( (-size * (1 - head_ratio),  0)               )
        myPath.relativeLineToPoint_( (0,                         -w * tail_width) )
        myPath.relativeLineToPoint_( (size * (1 - head_ratio),   0)               )
        myPath.relativeLineToPoint_( (0,                         -chin)           )
        myPath.closePath()
        myPath.transformUsingAffineTransform_(t)
        myPath.fill()
        
        drawPath(myPath)
        
        myString = NSString.string().stringByAppendingString_(kind)
        attrs = {
                NSFontAttributeName:            NSFont.systemFontOfSize_(label_size),
                NSForegroundColorAttributeName: NSColor.colorWithCalibratedRed_green_blue_alpha_( 0.4, 0.4, 0.6, 0.7 ),
        }
        bbox = myString.sizeWithAttributes_(attrs)
        #print bbox
        
        p = NSPoint()
        bw = bbox.width
        bh = bbox.height
        
        #print "   ", cos(angle)
        if -0.5 * pi < angle <= 0.5 * pi:
            p.x, p.y = (
                - size - 20 - bh/2 * sin(angle) - bw/2 * cos(angle), # + bw/2.0 * cos(angle - pi)
                0
            )
        else:
            p.x, p.y = (
                - size - 20 + bh/2 * sin(angle) + bw/2 * cos(angle), # + bw/2.0 * cos(angle - pi)
                0,
            )
        p = t.transformPoint_(p)
        #print p
        
        fontSize(label_size)
        #text(kind, (p.x - bbox.width/2, p.y - bbox.height/2))
        fill(None)
        rect(p.x - bbox.width/2, p.y - bbox.height/2, bbox.width, bbox.height)
        fill(1, 0, 0)
        oval(p.x -bh/2.0 , p.y -bh/2.0, bh, bh)
        #myString.drawAtPoint_withAttributes_(p, attrs)
        rr = NSRect(origin=(p.x -bh/2.0, p.y -bw/2.0), size=(bw, bh))
        print rr
        myString.drawInRect_withAttributes_(rr, attrs)
        

size(1000, 1000)

for i in range(20):
    #print degrees(i * 0.1 * pi)
    stroke(0.2)
    strokeWidth(1)

    fill(0.05 * i)
    
    angle = i * 0.1 * pi
    
    vector = (cos(angle), sin(angle))

    _drawArrow((500, 500), "Handgoloves FM", 300, vector, 18)
    fill(None)
    line((500, 1000), (500, 0))
    #break

saveImage("~/Desktop/Arrows.png")