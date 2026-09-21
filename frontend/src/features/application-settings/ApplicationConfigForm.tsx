import { Form, type FormInstance } from 'antd';
import type { ApplicationConfigUpdate } from '../../api/types';
import { QaCapabilitySettingsCard } from './QaCapabilitySettingsCard';

interface ApplicationConfigFormProps {
  form: FormInstance<ApplicationConfigUpdate>;
  onChange: () => void;
}

export function ApplicationConfigForm({ form, onChange }: ApplicationConfigFormProps) {
  return (
    <Form<ApplicationConfigUpdate> className="application-config-form" form={form} layout="vertical" onValuesChange={onChange}>
      <QaCapabilitySettingsCard />
    </Form>
  );
}
