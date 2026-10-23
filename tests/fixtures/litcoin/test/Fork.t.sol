contract F is Test { function setUp() public { vm.createSelectFork(vm.rpcUrl("mainnet")); } }
