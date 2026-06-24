import xml.etree.ElementTree as ET
import urllib.parse
from uuid import uuid4

class DrawioDiagram:
    def __init__(self):
        self.mxfile = ET.Element('mxfile', host='Electron', modified='2026-06-24T00:00:00.000Z', agent='Python script', etag='xyz', version='24.0.0', type='device')
        self.diagram = ET.SubElement(self.mxfile, 'diagram', name='Page-1', id=str(uuid4()))
        self.mxGraphModel = ET.SubElement(self.diagram, 'mxGraphModel', dx='1000', dy='1000', grid='1', gridSize='10', guides='1', tooltips='1', connect='1', arrows='1', fold='1', page='1', pageScale='1', pageWidth='827', pageHeight='1169', math='0', shadow='0')
        self.root = ET.SubElement(self.mxGraphModel, 'root')
        
        # Base cells
        ET.SubElement(self.root, 'mxCell', id='0')
        ET.SubElement(self.root, 'mxCell', id='1', parent='0')
        self.cell_counter = 2

    def next_id(self):
        vid = str(self.cell_counter)
        self.cell_counter += 1
        return vid

    def add_node(self, value, x, y, width, height, style, parent='1'):
        node_id = self.next_id()
        cell = ET.SubElement(self.root, 'mxCell', id=node_id, value=value, style=style, vertex='1', parent=parent)
        ET.SubElement(cell, 'mxGeometry', x=str(x), y=str(y), width=str(width), height=str(height), **{'as': 'geometry'})
        return node_id

    def add_edge(self, source, target, value="", style="", parent='1'):
        edge_id = self.next_id()
        if not style:
            style = "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;strokeColor=#666666;strokeWidth=2;fontColor=#333333;"
        cell = ET.SubElement(self.root, 'mxCell', id=edge_id, value=value, style=style, edge='1', parent=parent, source=source, target=target)
        geom = ET.SubElement(cell, 'mxGeometry', relative='1', **{'as': 'geometry'})
        return edge_id

    def save(self, filepath):
        tree = ET.ElementTree(self.mxfile)
        tree.write(filepath, encoding='utf-8', xml_declaration=True)

