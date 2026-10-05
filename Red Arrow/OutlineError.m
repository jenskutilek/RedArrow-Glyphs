//
//  OutlineError.m
//  Red Arrow
//
//  Created by Jens Kutilek on 05.10.26.
//
//

#import "OutlineError.h"

@implementation OutlineError

- (instancetype)initWithPosition:(NSPoint)point andSeverity:(uint8_t)severity {
    self = [super init];
    if (self) {
        self.position = &point;
        self.severity = severity;
    }
    return self;
}

@end
