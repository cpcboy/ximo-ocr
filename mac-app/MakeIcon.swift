import AppKit

guard CommandLine.arguments.count == 2 else {
    fputs("Usage: MakeIcon output.png\n", stderr)
    exit(2)
}

let canvas = NSSize(width: 1024, height: 1024)
let image = NSImage(size: canvas)
image.lockFocus()

let outerRect = NSRect(x: 44, y: 44, width: 936, height: 936)
let outerPath = NSBezierPath(roundedRect: outerRect, xRadius: 220, yRadius: 220)
let gradient = NSGradient(
    colors: [
        NSColor(calibratedRed: 0.25, green: 0.34, blue: 0.95, alpha: 1),
        NSColor(calibratedRed: 0.49, green: 0.29, blue: 0.90, alpha: 1)
    ]
)!
gradient.draw(in: outerPath, angle: -42)

let innerRect = NSRect(x: 116, y: 116, width: 792, height: 792)
NSColor.white.withAlphaComponent(0.10).setFill()
NSBezierPath(roundedRect: innerRect, xRadius: 150, yRadius: 150).fill()

let corners: [(NSPoint, NSPoint, NSPoint)] = [
    (NSPoint(x: 258, y: 718), NSPoint(x: 258, y: 790), NSPoint(x: 330, y: 790)),
    (NSPoint(x: 694, y: 790), NSPoint(x: 766, y: 790), NSPoint(x: 766, y: 718)),
    (NSPoint(x: 258, y: 306), NSPoint(x: 258, y: 234), NSPoint(x: 330, y: 234)),
    (NSPoint(x: 694, y: 234), NSPoint(x: 766, y: 234), NSPoint(x: 766, y: 306))
]

NSColor.white.withAlphaComponent(0.92).setStroke()
for points in corners {
    let path = NSBezierPath()
    path.lineWidth = 34
    path.lineCapStyle = .round
    path.lineJoinStyle = .round
    path.move(to: points.0)
    path.line(to: points.1)
    path.line(to: points.2)
    path.stroke()
}

let paragraph = NSMutableParagraphStyle()
paragraph.alignment = .center
let attributes: [NSAttributedString.Key: Any] = [
    .font: NSFont.systemFont(ofSize: 356, weight: .semibold),
    .foregroundColor: NSColor.white,
    .paragraphStyle: paragraph
]
("墨" as NSString).draw(
    in: NSRect(x: 0, y: 320, width: 1024, height: 440),
    withAttributes: attributes
)

image.unlockFocus()

guard
    let tiff = image.tiffRepresentation,
    let bitmap = NSBitmapImageRep(data: tiff),
    let png = bitmap.representation(using: .png, properties: [:])
else {
    fputs("Unable to render icon\n", stderr)
    exit(1)
}

try png.write(to: URL(fileURLWithPath: CommandLine.arguments[1]))
