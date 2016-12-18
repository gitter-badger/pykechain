import matplotlib.figure

from kechain2.models import Base


class Property(Base):

    def __init__(self, json):
        super(Property, self).__init__(json)

        self.output = json.get('output')

        self._value = json.get('value')

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        if isinstance(value, matplotlib.figure.Figure):
            self._attach_plot(value)
            self._value = '<PLOT>'
            return

        if value != self._value:
            self._put_value(value)
            self._value = value

    @property
    def part(self):
        from kechain2.api import part

        part_id = self._json_data['part']

        return part(pk=part_id)

    def _put_value(self, value):
        from kechain2.api import session, api_url, HEADERS

        r = session.put(api_url('property', property_id=self.id),
                        headers=HEADERS,
                        json={'value': value})

        assert r.status_code == 200, "Could not update property value"

    def _post_attachment(self, data):
        from kechain2.api import session, api_url, HEADERS

        r = session.post(api_url('property_upload', property_id=self.id),
                         headers=HEADERS,
                         data={"part": self._json_data['part']},
                         files={"attachment": data})

        assert r.status_code == 200, "Could not upload attachment"

    def _attach_plot(self, figure):
        import io
        buffer = io.BytesIO()

        figure.savefig(buffer, format="png")

        data = ('plot.png', buffer.getvalue(), 'image/png')

        self._post_attachment(data)