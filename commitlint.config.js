// commitlint config — enforces Conventional Commits 1.0.0 with Hammerfall's
// allowed types and scopes from V2 spec §"Conventional Commits — Enforced".
// See docs/stage1/Helm_T1_Launch_Spec_V2.md.

module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'feat',
        'fix',
        'refactor',
        'docs',
        'test',
        'chore',
        'ci',
        'build',
        'perf',
        'style',
        'revert',
      ],
    ],
    'scope-enum': [
      2,
      'always',
      [
        'memory',
        'runtime',
        'ui',
        'agent',
        'prompt',
        'infra',
        'ci',
        'docs',
        'migration',
        'repo',
        'auth',
        'obs',
        'ops',
      ],
    ],
    'scope-empty': [2, 'never'],
    'subject-case': [2, 'never', ['upper-case', 'pascal-case', 'start-case']],
    'subject-empty': [2, 'never'],
    'subject-full-stop': [2, 'never', '.'],
    'header-max-length': [2, 'always', 100],
  },
};
