/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: "no-circular-deps",
      severity: "error",
      from: {},
      to: { circular: true },
    },
    {
      name: "no-components-to-server",
      severity: "error",
      from: { path: "^components/" },
      to: { path: "^server/" },
    },
    {
      name: "no-server-to-ui",
      severity: "error",
      from: { path: "^server/" },
      to: { path: "^(app|components)/" },
    },
    {
      name: "no-lib-to-ui",
      severity: "error",
      from: { path: "^lib/" },
      to: { path: "^(app|components)/" },
    },
  ],
  options: {
    tsConfig: {
      fileName: "tsconfig.json",
    },
    doNotFollow: {
      path: "node_modules",
    },
    includeOnly: "^(app|components|lib|server)/",
    reporterOptions: {
      dot: {
        collapsePattern: "node_modules/[^/]+",
      },
    },
  },
};
