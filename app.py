from flask import Flask, jsonify, render_template
from airtable import Airtable

app = Flask(__name__)

# Configuration Airtable avec le nouveau jeton
base_id = 'app31lSJ8ivdDWqLz'  # Base ID
table_id = 'tbl0svsVHcYY2qxor'  # Table ID (All)
api_key = 'patvNhFbtZIPi95B0.d0594da3cf1f56a264b818f3d68fb618b617b9697448ac5b7f6630cc25a82c2e'  # Nouveau jeton API

# Connexion à Airtable
airtable = Airtable(base_id, table_id, api_key)

@app.route('/')
def home():
    try:
        # Récupérer toutes les questions depuis Airtable
        records = airtable.get_all()
        
        qcms_list = []
        for record in records:
            fields = record['fields']
            qcms_list.append({
                'id': record['id'],
                'question': fields.get('fld0lUvcwxsGipI5h'),  # Question
                'options': [
                    fields.get('fldaZUHYpBkqUqF2w'),  # Choix A
                    fields.get('fldbqIkiiRS6vfETr'),  # Choix B
                    fields.get('fld5bfd6T9Uj3gJzX'),  # Choix C
                    fields.get('fldjCZLO6sRI8O1pf')   # Choix D
                ],
                'correct_option': fields.get('fldtyNTs5dGFE7BCt')  # Bonne réponse
            })
        
        # Passer les QCMs au template HTML
        return render_template('index.html', qcms=qcms_list)
    except Exception as e:
        return f"Erreur lors de la récupération des données : {str(e)}"

@app.route('/qcms')
def get_qcms():
    try:
        records = airtable.get_all()
        return jsonify(records)
    except Exception as e:
        return jsonify({'error': 'Error retrieving data from Airtable', 'message': str(e)})

if __name__ == '__main__':
    app.run(debug=True)
