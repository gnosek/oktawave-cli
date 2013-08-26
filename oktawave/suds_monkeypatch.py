import logging
import suds
from suds import *
from suds.mx import *
from suds.resolver import Frame

# monkeypatching some of the suds code to allow object attributes starting with "_"
log = logging.getLogger(__name__)
def typed_start(self, content):
    log.debug('starting content:\n%s', content)
    if content.type is None:
        name = content.tag
        content.type = self.resolver.find(name, content.value)
        if content.type is None:
            raise TypeNotFound(content.tag)
    else:
        known = None
        if isinstance(content.value, Object):
            known = self.resolver.known(content.value)
            if known is None:
                log.debug('object has no type information', content.value)
                known = content.type
        frame = Frame(content.type, resolved=known)
        self.resolver.push(frame)
    frame = self.resolver.top()
    content.real = frame.resolved
    content.ancestry = frame.ancestry
    self.translate(content)
    self.sort(content)
    if self.skip(content):
        log.debug('skipping (optional) content:\n%s', content)
        self.resolver.pop()
        return False
    else:
        return True
suds.mx.literal.Typed.start = typed_start
def primative_append(self, parent, content):
    child = self.node(content)
    child.setText(tostr(content.value))
    parent.append(child)
suds.mx.appender.PrimativeAppender.append = primative_append
def element_append(self, parent, content):
    child = ElementWrapper(content.value)
    parent.append(child)
suds.mx.appender.ElementAppender.append = element_append
def text_append(self, parent, content):
    child = self.node(content)
    child.setText(content.value)
    parent.append(child)
suds.mx.appender.TextAppender.append = text_append



