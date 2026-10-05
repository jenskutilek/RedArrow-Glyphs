//
//  OutlineError.h
//  Red Arrow
//
//  Created by Jens Kutilek on 05.10.26.
//
//

#import <Cocoa/Cocoa.h>

// The OutlineError class

@interface OutlineError : NSObject

@property uint8_t severity;

@property NSPoint * position;

- (instancetype)initWithPosition:(NSPoint)point andSeverity:(uint8_t)severity;

@end
