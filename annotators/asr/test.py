import requests


def main():
    url = 'http://0.0.0.0:8031/asr_check'
    input_data = {'speeches': [{
        'hypotheses': [
            {
                  'tokens': [
                      {
                          'confidence': 0.95,
                          'value': "let's"
                      },
                      {
                          'confidence': 0.968,
                          'value': 'chat'
                      }
                  ]
                  }
        ]
    }]
    }
    result = requests.post(url, json=input_data)
    print(result.json())
    assert result.json()[0]['asr_confidence'] == 'high'

    input_data = {'speeches': [{
        'hypotheses': [
            {
                  'tokens': [
                      {
                          'confidence': 0.6,
                          'value': "let's"
                      },
                      {
                          'confidence': 0.6,
                          'value': 'chat'
                      }
                  ]
                  }
        ]
    }]
    }

    result = requests.post(url, json=input_data)
    assert result.json()[0]['asr_confidence'] == 'medium'

    input_data = {'speeches': [{
        'hypotheses': [
            {
                  'tokens': [
                      {
                          'confidence': 0.4,
                          'value': "let's"
                      },
                      {
                          'confidence': 0.4,
                          'value': 'chat'
                      }
                  ]
                  }
        ]
    }]
    }
    result = requests.post(url, json=input_data)
    assert result.json()[0]['asr_confidence'] == 'very_low'

    result = requests.post(url, json={'speeches': [[]]})
    assert result.json()[0]['asr_confidence'] == 'undefined'


if __name__ == '__main__':
    main()