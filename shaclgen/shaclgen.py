#!/usr/bin/env python


import collections
import json
from datetime import datetime
from urllib.parse import urlparse

import pkg_resources
import rdflib
from progressbar import Percentage, ProgressBar,Bar,ETA
from rdflib import Namespace, URIRef, BNode, Literal
from rdflib.namespace import RDF
from rdflib.util import guess_format


class data_graph():
    def __init__(self, args: list):
        self.G = rdflib.Graph()
        self.G.open("store", create=True)
        print(args)
        for graph in args:
            self.G.parse(graph, format=guess_format(graph))
        print("Finished loading graph....")
        print(len(self.G))
        self.CLASSES = collections.OrderedDict()
        self.PROPS = collections.OrderedDict()
        self.PROPS_NEW = collections.OrderedDict()
        self.OUT = []

        path = 'prefixes/namespaces.json'
        filepath = pkg_resources.resource_filename(__name__, path)

        with open(filepath, 'r', encoding='utf-8') as fin:
            self.names = json.load(fin)
        self.namespaces = []
        print(len(self.G))

    def parse_uri(self, URI):
        if '#' in URI:
            label = URI.split("#")[-1]
        else:
            label = URI.split("/")[-1]
        return label

    def gen_prefix_bindings(self):
        count = 0
        subs = []
        for s, p, o in self.G.triples((None, None, None)):
            subs.append(p)
        for s, p, o in self.G.triples((None, RDF.type, None)):
            subs.append(o)
        subs = list(set(subs))
        for pred in subs:
            if pred.replace(self.parse_uri(pred), '') not in self.names.values():
                count = count + 1
                self.names['ns' + str(count)] = pred.replace(self.parse_uri(pred), '')
        for pref, uri in self.names.items():
            for s in subs:
                if uri == s.replace(self.parse_uri(s), ''):
                    self.namespaces.append((pref, uri))
        self.namespaces = list(set(self.namespaces))

    def sh_label_gen(self, uri):
        parsed = uri.replace(self.parse_uri(uri), '')
        for cur, pref in self.names.items():
            if pref == parsed:
                return cur + '_' + self.parse_uri(uri)

    def uri_validator(self, x):
        try:
            result = urlparse(x)
            return all([result.scheme, result.netloc])
        except:
            return False

    def gen_shape_labels(self, URI):
        if '#' in URI:
            label = URI.split("#")[-1]
        else:
            label = URI.split("/")[-1]
        return label + '_'

    def extract_classes(self):
        print("INFO: extract_classes ...")
        classes = []
        for s, p, o in self.G.triples((None, RDF.type, None)):
            classes.append(o)
        print("INFO:  appended classes in classes array...")
        for c in sorted(classes):
            self.CLASSES[c] = {}
        count = 0
        print("INFO:  self.CLASSES[c] keys prepared for dict...")
        print("INFO:  Started iterating over self.Classes.keys dictionary")
        pbar = ProgressBar()
        for class_item in pbar(self.CLASSES.keys()):
            # self.CLASSES[class_item]['label'] = self.sh_label_gen(class_item)
            if (self.parse_uri(class_item)):
                self.CLASSES[class_item]['label'] = self.parse_uri(class_item) + "Shape"
            else:
                print("## error for class item " + class_item + " line 91-93 of file shaclgen.py")
        print("INFO: Loop Finished....")

    def extract_props(self):
        self.extract_classes()
        prop = []
        pbar = ProgressBar()

        print("INFO: Predicate appending ...")
        for predicate in self.G.predicates(object=None, subject=None):
            prop.append(predicate)

        print("INFO: RDF.Type prop loop....")
        props = [x for x in pbar(prop) if x != rdflib.term.URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')]

        print("INFO: Started preparing props keys....")
        for p in sorted(props):
            self.PROPS[p] = {}
        print("INFO: Finished preparing props keys....")
        count = 0
        print("INFO: Length of Props: " + str(len(self.PROPS)))

        print("INFO: Iterating over PROPS.Keys....")
        N = len(self.PROPS.keys())
        print(N)

        pbarr = ProgressBar(widgets=[Bar('>', '[', ']'), ' ', Percentage(), ' ', ETA()], maxval = N)

        for p in pbarr(self.PROPS.keys()):
            print(count)
            self.PROPS[p]['nodekind'] = None
            self.PROPS[p]['cardinality'] = None

            count = count + 1
            self.PROPS[p]['classes'] = []
            valProp = str(self.parse_uri(p))
            self.PROPS[p]['label'] = valProp
            prop_classes = []

            for sub, pred, obj in self.G.triples((None, p, None)):
                for sub1, pred1, obj1 in self.G.triples((sub, RDF.type, None)):
                    prop_classes.append(obj1)

            uris = []
            # pbarIn = ProgressBar(widgets=[Bar('>', '[', ']'), ' ', Percentage(), ' ', ETA()], maxval = len(prop_classes))
            [uris.append(x) for x in prop_classes if x not in uris]

            # counter = 0
            # pbarIn = ProgressBar(widgets=[Bar('>', '[', ']'), ' ', Percentage(), ' ', ETA()], maxval=len(uris))
            # print("INFO: Iterating over URIS")
            for x in uris:
                # Preparing a new Property
                # counter = counter + 1
                copyOfP = p
                if (self.CLASSES[x]['label']):
                    newProp = copyOfP + self.CLASSES[x]['label'] + "Property"
                    self.PROPS_NEW[newProp] = {}
                    self.PROPS_NEW[newProp]['classes'] = []
                    self.PROPS_NEW[newProp]['classes'].append(self.CLASSES[x]['label'])
                    self.PROPS_NEW[newProp]['label'] = self.parse_uri(newProp)
                    self.PROPS_NEW[newProp]['nodekind'] = None
                    self.PROPS_NEW[newProp]['cardinality'] = None
                    self.PROPS_NEW[newProp]['path'] = p
                    # old
                    self.PROPS[p]['classes'].append(self.CLASSES[x]['label'])
                else:
                    print("## else condition for self.CLASSES[x]['label'] " + x + " line 128 of file shaclgen.py")

            if len(self.PROPS[p]['classes']) == 1:
                self.PROPS[p]['type'] = 'unique'

            else:
                self.PROPS[p]['type'] = 'repeat'

    def extract_contraints(self):
        self.extract_props()
        print("INFO: Props extraction finished...")
        pbarInCon = ProgressBar(widgets=[Bar('>', '[', ']'), ' ', Percentage(), ' ', ETA()], maxval=len(self.PROPS_NEW.keys()))
        print("Iterating over extracted Properties")
        count = 0
        for prop in pbarInCon(self.PROPS_NEW.keys()):
            print(count)
            types = []
            for s, p, o in self.G.triples((None, self.PROPS_NEW[prop]['path'], None)):
                types.append(type(o))
            if len(set(types)) == 1:
                if types[0] == URIRef:
                    self.PROPS_NEW[prop]['nodekind'] = 'IRI'
                elif types[0] == BNode:
                    self.PROPS_NEW[prop]['nodekind'] = 'BNode'
                elif types[0] == Literal:
                    self.PROPS_NEW[prop]['nodekind'] = 'Literal'
            count = count + 1

    def gen_graph(self, serial='turtle', graph_format=None, namespace=None, verbose=None):
        # self.extract_props()
        print("INFO: gen_graph begin .....")
        self.gen_prefix_bindings()
        print("INFO: gen prefix bindings finished")
        self.extract_contraints()
        print("INFO: extract_constraints finished")
        print("INFO: now creating SHACL shapes...")
        ng = rdflib.Graph()
        SH = Namespace('http://www.w3.org/ns/shacl#')
        ng.bind('sh', SH)

        for x in self.namespaces:
            ng.bind(x[0], x[1])

        if namespace != None:
            if self.uri_validator(namespace[0]) != False:
                uri = namespace[0]
                if namespace[0][-1] not in ['#', '/', '\\']:
                    uri = namespace[0] + '#'
                EX = Namespace(uri)
                ng.bind(namespace[1], EX)
            else:
                print('##malformed URI, using http://example.org/ instead...')
                EX = Namespace('http://www.example.org/')
                ng.bind('ex', EX)
        else:
            EX = Namespace('http://www.example.org/')
            ng.bind('ex', EX)

        for c in self.CLASSES.keys():
            label = self.CLASSES[c]['label']
            ng.add((EX[label], RDF.type, SH.NodeShape))
            ng.add((EX[label], SH.targetClass, c))
            ng.add((EX[label], SH.nodeKind, SH.BlankNodeOrIRI))

        for p in self.PROPS_NEW.keys():
            ng.add((EX[self.PROPS_NEW[p]['label']], RDF.type, SH.PropertyShape))
            ng.add((EX[self.PROPS_NEW[p]['label']], SH.path, self.PROPS_NEW[p]['path']))
            # ng.add((EX[self.PROPS_NEW[p]['label']], RDF.type, SH.PropertyShape))
            # ng.add((EX[self.PROPS_NEW[p]['label']], SH.path, p))
            #
            for class_prop in self.PROPS_NEW[p]['classes']:
                ng.add((EX[class_prop], SH.property, EX[self.PROPS_NEW[p]['label']]))
            if self.PROPS_NEW[p]['nodekind'] == 'IRI':
                ng.add((EX[self.PROPS_NEW[p]['label']], SH.nodeKind, SH.IRI))
            elif self.PROPS_NEW[p]['nodekind'] == 'BNode':
                ng.add((EX[self.PROPS_NEW[p]['label']], SH.nodeKind, SH.BlankNode))
            elif self.PROPS_NEW[p]['nodekind'] == 'Literal':
                ng.add((EX[self.PROPS_NEW[p]['label']], SH.nodeKind, SH.Literal))

        # datetime object containing current date and time
        now = datetime.now()
        print("now =", now)

        # dd/mm/YY H:M:S
        dt_string = now.strftime("resources/SHACL_SHAPES_%H_%M_%S_%d_%m_%Y.ttl")
        print("date and time =", dt_string)

        print(ng.serialize(format=serial).decode())
        f = open(dt_string, "x")
        f.write(ng.serialize(format=serial).decode())
        f.close()
