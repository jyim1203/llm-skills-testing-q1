# Frozen 20-Task Mechanism Set

**Status:** frozen 2026-11-14

**Benchmark:** SWE-bench Pro V2 at `66f92766bba642462d4bbe5479e83f91f9211862`  
**Workflow:** v2 canonical (`586b13769c48f7fea32d0723a4948f58f016c14094063e3bf4606376f5dc78ab`)  
**Design:** 20 tasks x 3 conditions x 2 repeats = 120 attempts  
**Existing attempts:** 60 (`mechanism-pilot-01`)  
**New attempts:** 20 A + 40 B/C (planned)

This freezes the 10 new tasks selected after the A-only screens. The
original 10 tasks remain unchanged. No B/C outcomes were used for
selection. The accepted composition is 3 floor and 5 hard tasks;
observed A difficulty is reported alongside the intended label.

Full task IDs and machine-readable provenance are in
`data/mechanism-20-final/tasks.json`.

## Tasks

| # | Stratum | Repo | Task | Files / lines | F2P | P2P | A observed | Source |
|---:|---|---|---|---:|---:|---:|---|---|
| 1 | ceiling | ansible/ansible | `ansible-e22e10` | 2 / 30 | 4 | 26 | 2/2 resolved; 0/2 budget | `mechanism-20a-pilot-01` |
| 2 | ceiling | ansible/ansible | `ansible-e9e600` | 2 / 96 | 8 | 20 | 2/2 resolved; 0/2 budget | `mechanism-pilot-01` |
| 3 | ceiling | internetarchive/openlibrary | `openlibrary-e80841` | 1 / 29 | 1 | 58 | 2/2 resolved; 0/2 budget | `mechanism-20a-pilot-01` |
| 4 | ceiling | qutebrowser/qutebrowser | `qutebrowser-3e21c8` | 1 / 59 | 1869 | 0 | 2/2 resolved; 2/2 budget | `mechanism-pilot-01` |
| 5 | easy | ansible/ansible | `ansible-12734f` | 3 / 26 | 1 | 4 | 2/2 resolved; 0/2 budget | `mechanism-pilot-01` |
| 6 | easy | ansible/ansible | `ansible-83fb24` | 2 / 22 | 1 | 21 | 2/2 resolved; 0/2 budget | `mechanism-20a-pilot-01` |
| 7 | easy | qutebrowser/qutebrowser | `qutebrowser-96b997` | 2 / 24 | 17 | 161 | 2/2 resolved; 0/2 budget | `mechanism-pilot-01` |
| 8 | easy | qutebrowser/qutebrowser | `qutebrowser-990291` | 5 / 77 | 4 | 58 | 2/2 resolved; 0/2 budget | `mechanism-20a-screen-02` |
| 9 | floor | ansible/ansible | `ansible-1c06c4` | 4 / 71 | 4 | 21 | 0/2 resolved; 2/2 budget | `mechanism-20a-pilot-01` |
| 10 | floor | internetarchive/openlibrary | `openlibrary-0dc5b2` | 1 / 62 | 6 | 55 | 0/2 resolved; 2/2 budget | `mechanism-pilot-01` |
| 11 | floor | internetarchive/openlibrary | `openlibrary-b67138` | 6 / 888 | 11 | 53 | 0/2 resolved; 2/2 budget | `mechanism-pilot-01` |
| 12 | hard | ansible/ansible | `ansible-b748ed` | 5 / 269 | 5 | 41 | 1/2 resolved; 1/2 budget | `mechanism-20a-screen-03` |
| 13 | hard | ansible/ansible | `ansible-d62496` | 3 / 35 | 22 | 92 | 2/2 resolved; 0/2 budget | `mechanism-pilot-01` |
| 14 | hard | internetarchive/openlibrary | `openlibrary-630221` | 6 / 328 | 9 | 0 | 1/2 resolved; 2/2 budget | `mechanism-20a-screen-03` |
| 15 | hard | qutebrowser/qutebrowser | `qutebrowser-c09e14` | 4 / 45 | 5 | 100 | 0/2 resolved; 0/2 budget | `mechanism-pilot-01` |
| 16 | hard | qutebrowser/qutebrowser | `qutebrowser-ec2dcf` | 4 / 96 | 7 | 6 | 2/2 resolved; 2/2 budget | `mechanism-20a-screen-02` |
| 17 | medium | ansible/ansible | `ansible-5e3696` | 5 / 94 | 7 | 2 | 2/2 resolved; 2/2 budget | `mechanism-pilot-01` |
| 18 | medium | ansible/ansible | `ansible-6cc974` | 7 / 83 | 8 | 55 | 2/2 resolved; 0/2 budget | `mechanism-20a-screen-02` |
| 19 | medium | internetarchive/openlibrary | `openlibrary-6e889f` | 2 / 104 | 7 | 10 | 1/2 resolved; 1/2 budget | `mechanism-20a-screen-02` |
| 20 | medium | internetarchive/openlibrary | `openlibrary-d8162c` | 3 / 74 | 18 | 0 | 2/2 resolved; 1/2 budget | `mechanism-pilot-01` |

## Composition

- Strata: ceiling 4, easy 4, floor 3, hard 5, medium 4
- Repos: ansible/ansible 9, internetarchive/openlibrary 6, qutebrowser/qutebrowser 5
- Conditions: A, B, C
- Repeats: 2
- Total attempts: 120

## Provenance

| Task | Task checksum | Image digest |
|---|---|---|
| `ansible-e22e10` | `5070c3ca9451b3dac769d0b74afb8dc2872daa9ae0e65e3fad69d5737578be55` | `sha256:a641182b5ee252b8250b2ef85f62510f5d87dbeb4bb45db90e57cd7e7bd83995` |
| `ansible-e9e600` | `11fc8efba32735cea706b95bf25f5810f5ad6f369e82554a7705209500694f37` | `sha256:92f0dd38d06484c811b6ce83db04e012e0e2a6456c48dc8b67099d740d3244c7` |
| `openlibrary-e80841` | `25ee138eb8a5bcbe00854c81c43964f882832eec49d051669718e99539ad42a8` | `sha256:ed6004c1632836bd1ed7d02d0eb9422ab364ecda14a6eec082cbbaa70217a040` |
| `qutebrowser-3e21c8` | `633ea85b0766adca15e5ba73d4090c32bee55ec93f5898e755b90fabc7b03741` | `sha256:b35c588560c0041a3d0989696ade4a1ae1e5123e3e07b27240fb918d16237747` |
| `ansible-12734f` | `acaf8bd229da1aa0eae5238f6087920cb5eb724955eb1cf002ce8fd61d635b66` | `sha256:dbcace12df34d7d635682b7c598c0579109c52ced4818c3942a4ad3a5da79b04` |
| `ansible-83fb24` | `c2e986aea40654bfc4520b497ae0c13caf0c3378ca82ffaf593bf7c598189b91` | `sha256:e82fbe5d87fa3ce9c8bd90767dc83925eda835261e188e3419b1d5c068d96095` |
| `qutebrowser-96b997` | `0b4a5a82ba395fbbfb963417b2bd585d9d07f4f30c6562264561a587096e917b` | `sha256:19bb9d9ad2670ee924dc75a69f6ba215ff9fa32d93874009d2d105d9368be9f0` |
| `qutebrowser-990291` | `4f24bff1f8892ea6b6049c914154a000072ae8d26f8f39cda2f711d391fb5e37` | `sha256:50b9b71bdcbd048786055b9957690fc4210f7f16dc4c93b680ea06c113130846` |
| `ansible-1c06c4` | `cc3133aed059a0dde47a765b00d66779be3de9aace82560b7f270b152ca8ff2f` | `sha256:2ee62346a660d4329f1b4126ecadd02291a0ffca97939c478fbe2b4683dc3e5e` |
| `openlibrary-0dc5b2` | `affea468953fbc1c9c2ec9e6459bd6ddc446d26d7467a6a02e5d17d228ab4fd8` | `sha256:8780cafe8ec369b6138b9fef049d5cfff1a3729364692ad5c5b1c0666cd0411d` |
| `openlibrary-b67138` | `a9fcbe05a4d9b07404e0f3d8072e533a546b6cb3d85cc0676eb20b4623099d23` | `sha256:d1869bd5a264044c7b58a948422e2d6b457385e34077bafaa68191bc5be46440` |
| `ansible-b748ed` | `2aed993b9bdda33ffdac4bc19b92ff29f640c05231cddc4f78a5a6296219a8f8` | `sha256:f543293f942bf3593e4674dd8f720df8ecf2884ec4833e501225953267da98b3` |
| `ansible-d62496` | `c564af0fc728603d20995b6aa06b476b2ddf57c4c7ec822519ce0fb93acee8e9` | `sha256:2c6d53c235a04be7c6f188bf7004a9bc3b94a1f7ad058ae43b786259dbe0123f` |
| `openlibrary-630221` | `a753d85feef98b60c613d764dfafc0ece846c86e97873343c31f2753dce1293f` | `sha256:a5da56787aa6f4ad32a3dbcff7091f5f584c932dfbb402287f9de85793e7c2b1` |
| `qutebrowser-c09e14` | `98423b7930f71a628915f06f18ab6ee5d8193747cda2c2b3bfd96f3ad7a7d08a` | `sha256:a67d0f526e5ea0fd7feadab688cb31865a3029c62c89fbf7439f26d14f488127` |
| `qutebrowser-ec2dcf` | `4c17ce6aab9295f1d686e94f8e4b085ed53a7ba1a93bb9c04b52bbba44593ff0` | `sha256:695e8bc32325be137805b3a0adbf42a879b0a77cea6d1f16511d7ba286c6ae25` |
| `ansible-5e3696` | `bd5d481be0a93bc619ee0534a88ad89e90dd7cda6571bb129ff49bad3d4dcdc3` | `sha256:4bbb2890557d722e440af44e54eb23e1b3c5dad20e91827e32f04bdb4107433f` |
| `ansible-6cc974` | `c60709f6ae399d71021062c0808d182f330df4e66a8cf73327900c2cda0b2faa` | `sha256:ddddc0e862e50855047766e747582baa6a39dafc8f8fac4da8b83c3085c1f35f` |
| `openlibrary-6e889f` | `65dfb5ee1b3cc15c60d604f2cafd57c654d2f6f48e7ea0a289d625a017c0abe2` | `sha256:208c9774dee362861c7b62519f14a87e5a8a97ab2c95a6711fc9d3a439283edb` |
| `openlibrary-d8162c` | `3d4f020d6519d9b5f9e5b91d7c85b0483dfcf5c566bb800897f2104ff154987f` | `sha256:dba727b35e39c0e76dff3dcaf2804110028f609e655fa7e908930af9c1d0e5e9` |

## Freeze decisions

- Kept the original 10 tasks unchanged.
- Added 10 new tasks selected only from A-only screens.
- Dropped `openlibrary-53d376` as redundant with the other
  token-capped 2/2 tasks.
- Kept `openlibrary-630221` as a hard/budget candidate despite the
  original `b67138` alternative note; both are now in the 20-task set.
- Accepted the 3-floor / 5-hard composition rather than screening
  further; the observed A outcomes are recorded in the task table.
- No task changes after B/C outcomes.

## Freeze checklist

- [x] 20 unique task IDs
- [x] all task IDs present in the Pro V2 checkout
- [x] one task checksum and image digest per task
- [x] 10 existing tasks retained
- [x] 10 new tasks selected from A-only evidence
- [x] C-B not used for selection
- [x] no replacement after B/C outcomes
- [ ] B/C execution plan generated
- [ ] 120-attempt combined analysis completed
