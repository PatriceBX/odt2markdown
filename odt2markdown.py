import sys
import os

from . import main

from odf.opendocument import load
from odf.table import Table, TableRow, TableCell


class OdfStyle:
    def __init__(self):
        self.name= ''
        self.font_name= ''
        self.font_weight= ''
        self.font_style= ''
        self.dict= None


def odf_load(odf_file):
    odfdoc =  load(odf_file)
    styles = odf_get_styles(odfdoc)
    # Embedd the styles dict into the odfdoc object, so that odf_xxx functions can retrieve
    # Given a node, functions can reach styles by node.ownerdocument.my_readable_styles
    odfdoc.my_readable_styles = styles

    return odfdoc


def odf_get_styles(odfdoc):

    FONT_WEIGHT_KEY= 'text-properties/font-weight'
    FONT_NAME_KEY= 'text-properties/font-name'
    FONT_STYLE_KEY= 'text-properties/font-style'

    styles= {}
    for ast in odfdoc.automaticstyles.childNodes:

        name= ast.getAttribute('name')
        style= OdfStyle()
        styles[name]= style
        style.name= name

        style.dict= scan_style(ast)
        style_keys= style.dict.keys()

        if FONT_WEIGHT_KEY in style_keys:
            style.font_weight= style.dict[FONT_WEIGHT_KEY]
        if FONT_NAME_KEY in style_keys:
            style.font_name= style.dict[FONT_NAME_KEY]
        if FONT_STYLE_KEY in style_keys:
            style.font_style= style.dict[FONT_STYLE_KEY]

    return styles

def odf_process_span_spaces(span_node):
    t_out= u''
    for n in span_node.childNodes:
        if n.nodeType==1:   # element
            # Possible <text:s text:c="n"/> node
            if n.qname[1] == "s":
                t_out+= odf_process_space(n)
            else:
                print "Unhandled node under span, qname[1]= ", n.qname[1]
        elif n.nodeType==3:  # text
            t_out+= n.data
    if t_out=='':
        t_out= ' '
    return t_out


def odf_process_space(s_node):
    str_value= odf_node_get_attribute_value(s_node, "c")
    if str_value:
        value= int(str_value)
    else:
        value= 1
    t_out= " "*value
    return t_out


def odf_get_node_style(node):

    try:
        node_style = node.getAttribute('stylename')
    except AttributeError:
        node_style = None

    try:
        styles= node.ownerDocument.my_readable_styles
    except:
        print "my_readable_styles not embedded in owner document.  Call odf_get_styles first !"

    if node_style is None or node_style not in styles:
        style = None
    else:
        style = styles[node_style]

    return style


def odf_is_span_code(span_node):
    style = odf_get_node_style(span_node)
    if style is None or style.font_name == '':
        return 'no style'
    if 'Courier' in style.font_name:
        return 'code'
    else:
        return 'no code'


def odf_p_is_all_code(p, p_is_code):
    p_has_code = False
    p_has_nocode = False
    p_has_nofont = False
    for node in p.childNodes:
        if node.nodeType == 1:    # element
            if node.qname[1] == "span":
                span_is_code = odf_is_span_code(node)
                span_is_space = odf_process_span_spaces(node).strip()==''
                if not span_is_space:
                    if span_is_code=='no code':
                        p_has_nocode= True
                    elif span_is_code=='code':
                        p_has_code= True
                    else:
                        p_has_nofont= True
        elif node.nodeType == 3:   # Text
            if p_is_code:
                p_has_code = True
            else:
                p_has_nocode= True

    if p_is_code:   # The overall style of the paragraph is code (courier font)
        if p_has_nocode:   # There are spans with no code (font specified and other than courier)
            return False        # Not all code
        else:
            return True
    else:  # Overall style of paragraph is not code
        if p_has_code and not p_has_nocode and not p_has_nofont:  #  Only code spans were found
            return True
        else:
            return False



def odf_process_span(span_node, handle_code=True):

    span_w_spaces= odf_process_span_spaces(span_node)

    style = odf_get_node_style(span_node)

    if style is None:
        return span_w_spaces

    s_text = markdown(span_w_spaces, style, handle_code=handle_code)

    return s_text


def markdown(text, style, handle_code=True):
    if text.strip() == '':
        return text

    if handle_code and 'Courier' in style.font_name:
        out= '`' + text + '`'
    elif style.font_weight == 'bold':
        out= '__' + text + '__'
    elif style.font_style == 'italic':
        out= '_' + text + '_'
    else:
        out= text
    return out


def odf_process_p(p_node):
    t_out= u''

    p_style = odf_get_node_style(p_node)
    p_is_code= False
    if p_style is not None:
        if p_style.font_name.startswith('Courier'):
            p_is_code = True

    p_all_code= odf_p_is_all_code(p_node, p_is_code)

    handle_code= not p_all_code  # If p is made only of spans with code (or empty),

    for n in p_node.childNodes:
        if n.nodeType==1:    # element
            #n_type= node_get_type(n)
            if n.qname[1] == "span":
                t_out+= odf_process_span(n, handle_code=handle_code)
            elif n.qname[1] == "s":
                t_out+= odf_process_space(n)
            elif n.qname[1] == "soft-page-break":
                pass
            else:
                print "Unhandled node under p: ", n.qname[1]
        elif n.nodeType==3:  # text
            t_out+= n.data
        else:
            print "Unhandled nodeType in p: ", n.nodeType

    if p_style is None:
        return t_out

    if p_all_code:
        t_out = '    ' + t_out
    else:
        t_out= markdown(t_out, p_style)

    return t_out


def odf_process_nodes(start_node, handle_cr=True):
    '''
    Process all nodes within given start node
    '''

    lines= []
    for n in start_node.childNodes:
        if n.qname[1]== 'p':
            lines.append(odf_process_p(n))
        elif n.qname[1]== 'list':
            lines.append(odf_process_list(n))
        else:
            print "Unhandled node in ", start_node.qname[1], ": ", n.qname[1]

    if handle_cr:
        # Handle \n depending on code sections
        in_code= False
        out= ''

        for line in lines:
            if in_code:
                if line.startswith('    ') or line.strip()=='':
                    # Remains in code section
                    out+= '\n' + line
                elif line.startswith('* '):
                    # NOTE that here a whole list comes as a single line item
                    out+= line
                    in_code= False
                else:
                    # Leaving code section
                    out+= '\n\n' + line
                    in_code= False
            else:
                # Not in code section
                if line.startswith('    '):
                    # Entering code section
                    out+= '\n\n' + line
                    in_code= True
                elif line.startswith('* ') or line.startswith('\n* '):
                    # NOTE that here a whole list comes as a single line item
                    out+= '\n' + line
                else:
                    # Remaining in no section
                    out+= '\n\n' + line
    else:
        # Option to not handle double \n, used when processing list items
        out= '\n'.join(lines)

    return out


def odf_process_list(list_node):
    '''
    Process childNodes of a node of type list (qname[1]=='list')
    '''
    items= []
    for n in list_node.childNodes:
        if n.qname[1]=='list-item':
            items.append(odf_process_nodes(n, handle_cr=False))
        else:
            print "Unhandled element type ", n.qname[1], " in node ", list_node.qname[1]

    out= ''
    for i in items:
        out+= "\n* " + i

    out += "\n\n<!-- -->"   # Trick to separate list from code bloc

    return out


def odf_parse_extract_table(doc=None, node= None, messages=[]):

    if doc is None and node is None:
        raise Exception(__name__, 'arguments cannot all be None')

    if doc is None:
        doc= node.ownerDocument
    elif node is None:
        node= doc.text

    ttab= []

    for table in node.getElementsByType(Table):
        for row in table.getElementsByType(TableRow):
            c= 0
            for cell in row.getElementsByType(TableCell):

                if c==0:
                    content_code= str(cell).strip()

                elif c==1:
                    if content_code in ['question', 'answer_true', 'answer_false', 'rule', 'feedback']:
                        content_data= odf_process_nodes(cell)
                    else:
                        content_data= str(cell).strip()
                else:
                    messages.append("table has more than 2 columns")

                c+= 1

            trow= { 'content_code': content_code, 'content_data': content_data }
            ttab.append(trow)

    return ttab


def scan_style(s):
    style= {}
    for k in s.attributes.keys():
        style[k[1]]= s.attributes[k]
    for n in s.childNodes:
        for k in n.attributes.keys():
            style[n.qname[1] + "/" + k[1]]= n.attributes[k]
    return style


def odf_node_get_attribute_value(n, attr):
    value= None
    for k in n.attributes:
        if k[1] == attr:
            value= n.attributes[k]
            break
    return value


def odf_dump_nodes(start_node, level=0):
    if start_node.nodeType==3:
        # text node
        print "  "*level, "NODE:", start_node.nodeType, ":(text):", str(start_node)
    else:
        attrs= []
        for k in start_node.attributes.keys():
            attrs.append( k[1] + ':' + start_node.attributes[k]  )
        print "  "*level, "NODE:", start_node.nodeType, ":", start_node.qname[1], " ATTR:(", ",".join(attrs), ") ", str(start_node)

        for n in start_node.childNodes:
            odf_dump_nodes(n, level+1)
    return


def odf_dump_styles(odfdoc):
    for ast in odfdoc.automaticstyles.childNodes:
        name= ast.getAttribute('name')
        print "\nname: ", name
        for k in ast.attributes.keys():
            attr_name= ast.attributes[k]
        for n in ast.childNodes:
            for k in n.attributes.keys():
                print n.qname[1] + "/" + k[1] + "=" + n.attributes[k]



