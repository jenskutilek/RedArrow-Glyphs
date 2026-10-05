//
//  Red_Arrow.h
//  Red Arrow
//
//  Created by Jens Kutilek on 05.10.26.
//  
//

#import <Cocoa/Cocoa.h>
#import <GlyphsApp/GlyphsReporterProtocol.h>
#import <GlyphsCore/GlyphsCore.h>

@interface Red_Arrow : NSObject <GlyphsReporter>

@property float upm;

// Check runners based on node type

- (void)runCubicCurveChecks:(GSNode *)node;

- (void)runLineChecks:(GSNode *)node;

- (void)runOffcurveChecks:(GSNode *)node;

- (void)runQuadraticCurveChecks:(GSNode *)node;

// Specific node checks

- (void)checkNearlySmoothConnection:(GSNode *)node;

@end
