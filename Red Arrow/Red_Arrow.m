//
//  Red_Arrow.m
//  Red Arrow
//
//  Created by Jens Kutilek on 05.10.26.
//  
//

#import "Red_Arrow.h"
#import "OutlineError.h"
#import <GlyphsApp/GlyphsApp.h>
#import <GlyphsCore/GlyphsCore.h>


@implementation Red_Arrow

@synthesize controller = _editViewController;

- (instancetype)init {
	self = [super init];
	if (self) {
        self.upm = 1000;
        self.RedArrowSmoothMaxDistance = 8;
	}
	return self;
}

- (NSUInteger)interfaceVersion {
	// Distinguishes the API version the plugin was built for. Return 1.
	return 1;
}

- (NSString *)title {
	// This is the name as it appears in the menu in combination with 'Show'.
	// E.g. 'return @"Nodes";' will make the menu item read "Show Nodes".
	return NSLocalizedStringFromTableInBundle(@"Red Arrow", nil, [NSBundle bundleForClass:[self class]], @"DESCRIPTION");
}

- (NSString *)keyEquivalent {
	// The key for the keyboard shortcut. Set modifier keys in modifierMask further below.
	// Pretty tricky to find a shortcut that is not taken yet, so be careful.
	// If you are not sure, use 'return nil;'. Users can set their own shortcuts in System Prefs.
	return nil;
}

- (NSEventModifierFlags)modifierMask {
	// Use any combination of these to determine the modifier keys for your default shortcut:
	// return NSShiftKeyMask | NSControlKeyMask | NSCommandKeyMask | NSAlternateKeyMask;
	// Or:
	// return 0;
	// ... if you do not want to set a shortcut.
	return 0;
}


- (void)drawForegroundForLayer:(GSLayer *)layer options:(NSDictionary *)options {
    // Update the outline check on each draw for now
    [self.errors removeAllObjects];
    [self updateOutlineReport:layer options:options];
    
    // Draw the arrows
    for (OutlineError * error in self.errors) {
        NSRect rect = NSMakeRect(error.position->x, error.position->y, 10, 10);
        [[NSColor blueColor] set];
        [NSBezierPath fillRect:rect];
    }
	
}


- (float)normalizeForUpm:(float)value {
    return value * self.upm * 0.001;
}


- (void)updateOutlineReport:(GSLayer *)layer options:(NSDictionary *)options {
    NSLog(@"updateOutlineReport: %@", layer.name);
    self.upm = layer.parent.parent.unitsPerEm;
    // self.RedArrowSmoothMaxDistance = [self normalizeForUpm: self.RedArrowSmoothMaxDistance];
    for (GSPath* path in layer.paths) {
        NSUInteger numNodes = path.countOfNodes;
        GSNode * prev = path.nodes[numNodes - 1];
        GSNode * next = path.nodes[1];
        for (NSUInteger i = 0; i <= numNodes; i++) {
            GSNode * node = path.nodes[i];
            switch (node.type) {
                case GSNodeTypeCubicCurve:
                    [self runCubicCurveChecks: node];
                    break;
                
                case GSNodeTypeLine:
                    [self runLineChecks: node previousNode: prev nextNode: next];
                    break;
                
                case GSNodeTypeOffCurve:
                    [self runOffcurveChecks: node];
                    break;
                    
                case GSNodeTypeQuadraticCurve:
                    [self runQuadraticCurveChecks: node];
                    break;
                
                default:
                    break;
            }
            prev = node;
            if (i == numNodes) {
                // Roll over to first node
                next = path.nodes[0];
            } else {
                next = path.nodes[i+1];
            }
        }
    }
    
    // TODO: Component checks
}


- (void)runCubicCurveChecks:(GSNode *)node {
    
}

- (void)runQuadraticCurveChecks:(GSNode *)node {
    
}

- (void)runLineChecks:(GSNode *)node previousNode:(GSNode *)previousNode nextNode:(GSNode *)nextNode {
    [self checkNearlySmoothConnection: node previousNode: previousNode nextNode: nextNode];
}

- (void)runOffcurveChecks:(GSNode *)node {
    
}

// Specific checks

- (void)checkNearlySmoothConnection:(GSNode *)node previousNode:(GSNode *)previousNode nextNode:(GSNode *)nextNode {
    if (!previousNode || !nextNode) {
        return;
    }
        
    float dist1 = [GSGeometry distance:previousNode.position toPoint:node.position];
    float dist2 = [GSGeometry distance:node.position toPoint:nextNode.position];
    
    float dist;
    float phi;
    GSNode * ref;
    
    // The longer segment will be the reference
    if (dist1 >= dist2) {
        dist = dist2;
        phi = [GSGeometry angleBetweenVector:previousNode.position andVector:node.position];
        ref = nextNode;
    } else {
        dist = dist1;
        phi = [GSGeometry angleBetweenVector:node.position andVector:nextNode.position] - M_PI;
        ref = previousNode;
    }
    
    // Ignore short segments
    if (dist <= 2 * [self normalizeForUpm: self.RedArrowSmoothMaxDistance]) {
        return;
    }
    
    NSPoint projectedPt = NSMakePoint(node.position.x + dist * cos(phi), node.position.y + dist * sin(phi));
    GSNode * roundedNode = [[GSNode alloc] initWithPosition: projectedPt type: GSNodeTypeOffCurve connection: GSNodeConnectionSmooth];
    roundedNode.position = projectedPt;
    [roundedNode roundToGridFast: GSUnitGrid];
    float badness = [GSGeometry distance:roundedNode.position toPoint:ref.position];
    
    float d;
    if (self.gridLength == 0) {
        d = 0.49;
    } else {
        d = self.gridLength;
    }
    if (badness > d) {
        if (node.connection == GSNodeConnectionSmooth && badness < self.RedArrowSmoothMaxDistance) {
            [self.errors addObject: [[OutlineError alloc] initWithPosition: node.position andSeverity: 1]];
        }
    }
}


- (float)getScale {
	// [self getScale]; returns the current scale factor of the Edit View UI.
	// Divide any scalable size by this value in order to keep the same apparent pixel size.
	
	if (_editViewController) {
		return _editViewController.graphicView.scale;
	}
	else {
		return 1.0;
	}
}

@end
