export default {
  extends: ['stylelint-config-standard'],
  plugins: ['stylelint-declaration-strict-value'],
  rules: { 'selector-class-pattern': '^[a-z][a-zA-Z0-9]*$',
    'scale-unlimited/declaration-strict-value': [['color','background-color','z-index','transition-duration','padding','gap','margin'], { ignoreValues: ['0','auto','inherit','transparent','currentColor','none'] }],
    'declaration-property-value-disallowed-list': { 'z-index': ['/^[0-9]+$/'] },
  },
  overrides: [{ files: ['src/styles/tokens.css'], rules: { 'scale-unlimited/declaration-strict-value': null,'declaration-property-value-disallowed-list':null } }],
};
