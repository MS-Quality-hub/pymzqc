#sudo apt update
#sudo apt install python3 python3-pip python3-flask 
#pip install Flask
#pip install git+https://github.com/MS-Quality-hub/pymzqc.git@v1.0.0
#pip install flask-restful
#pip install gunicorn

import json
from flask import Flask
from flask import Flask, jsonify, request
from flask_restful import Resource, Api
from flask_cors import CORS

from mzqc.MZQCFile import MzQcFile as mzqc_file
from mzqc.MZQCFile import JsonSerialisable as mzqc_io
from mzqc.SemanticCheck import SemanticCheck
from mzqc.SyntaxCheck import SyntaxCheck

app = Flask(__name__)
api = Api(app)
CORS(app)

class Status(Resource):
    def get(self):
        try:
            return {'status': 'API is running', 'endpoints': ['status', 'documentation', 'validator']}
        except:
            return {'status': 'API fetch was unsuccessful'}

class Documentation(Resource):
    def get(self):
        api_doc_string = """
        The API call for `Validator` responds with a JSON object, nested for each validation mode: 
        `semantic validation` and `schema validation`. For each mode, the value will be a list of 
        validation items found to not (completely) correspond to the standard format.
        """

        semantic_doc_string = """
        The value to the 'semantic validation' key is an array of checks performed 
        on the deserialised mzQC object according to the latest specification. 
        The checks are the following:
        * 'general': 
            Check object given to validation is compatible
        * 'ontology term errors': 
            Verify that each CV term used exists in the CV
            Check that all CVs referenced are linked to a valid ontology
        * 'metric uniqueness': 
            Check that metrics (qualityMetrics are unique within a run/setQuality
        * 'input files':
            Verify that input files (metadata) are consistent and unique
        * 'label uniqueness':
            Verify that label (metadata) must be unique in the file
        * Verify that all columns in tables have same length
        * 'ontology load errors'
            Check if ontologies are listed multiple times (different versions etc)
        * 'value type errors':
            Check that cv term values are of type as defined in ontology
            Verify that each cv term in file and obo must match in all id,name,type
        * 'metric usage errors':
            Check that all qulaityMetrics are actually of metric type/relationship
            Check that cv terms have all attributes referred to in the CV
        """

        syntactic_doc_string = """
        The value to the 'schema validation' key is the parsed result to the JSONschema 
        validation of given file, using the current schema (unless stated otherwise).
        """
        
        return {'documentation': { 'schema validation': syntactic_doc_string, 'semantic validation': semantic_doc_string}}

class Validator(Resource):
    def post(self):
        default_unknown = jsonify({"general": "No mzQC structure detectable."})
        inpu = request.form.get('validator_input', None)
        try:
            target = mzqc_io.FromJson(inpu)
        except Exception as e:
            return default_unknown

        if type(target) != mzqc_file:
            return default_unknown
        else:
            removed_items = list(filter(lambda x: not x.uri.startswith('http'), target.controlledVocabularies))
            target.controlledVocabularies = list(filter(lambda x: x.uri.startswith('http'), target.controlledVocabularies))
            sem_val_res = SemanticCheck().validate(target)
            #print(sem_val_res)
            
            proto_response = {k: [str(i) for i in v] for k,v in sem_val_res.items()}
            proto_response.update({"unrecognised CVs": [str(it) for it in removed_items]})
            #print(proto_response)
            valt = mzqc_io.ToJson(target)
            syn_val_res = SyntaxCheck().validate(valt)
            # older versions of the validator report a generic response in an array - return first only
            if type(syn_val_res.get('schema validation', None)) == list:
                syn_val_res = {'schema validation': syn_val_res.get('schema validation', None)[0] if syn_val_res.get('schema validation', None) else ''}
            proto_response.update(syn_val_res)

            print(json.dumps(proto_response, indent=4, sort_keys=True))            
            # convert val_res ErrorTypes to strings
            # add note on removed CVs
            return jsonify(proto_response)
        return default_unknown

api.add_resource(Status, '/','/status/')
api.add_resource(Documentation, '/documentation/')
api.add_resource(Validator, '/validator/')

if __name__ == '__main__':
    app.run()
