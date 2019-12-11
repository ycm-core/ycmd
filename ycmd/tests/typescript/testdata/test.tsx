import * as React from 'react';

interface MyComponentProps {
  children: any;
}

const TestComponent: React.FunctionComponent<MyComponentProps> = (props) => {
  return (
    <div>
      <Bar />
      {props.children}
    </div>
  );
};

const a = { 'foo': 3 }
a.
