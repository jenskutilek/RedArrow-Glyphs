from __future__ import division

size(20, 20)
scale(1, -1)
translate(0, -20)
x = 3
y = 3
width = 2
size = 7
save()
translate(4, 4)

stroke(0.2)
strokeWidth(1)
lineJoin("miter")
fill(0.9, 0.4, 0.3)
rect(-1, -1, size+1, size+1)
#rect(0, 0, size, size)

lineJoin("round")
lineCap("butt") # butt, square, round
strokeWidth(width)
stroke(1, 0.9, 0.65)
line((0, width / 2 - 0.5), (size - width / 2 + 0.5, width / 2 - 0.5))
line((width / 2 - 0.5, width / 2 - 1.5), (width / 2 - 0.5, size-width / 2 + 0.5))
lineCap("round")
line((width//2, width//2), (size-1.5, size-1.5))

restore()