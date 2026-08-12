import type { Preview } from "@storybook/react-vite";
import { withThemeByDataAttribute } from "@storybook/addon-themes";
import { mswLoader } from "msw-storybook-addon/csf3";

import "../src/styles/index.css";

const preview: Preview = {
  decorators: [
    withThemeByDataAttribute({
      themes: {
        light: "light",
        dark: "dark",
      },
      defaultTheme: "light",
      attributeName: "data-theme",
    }),
  ],
  loaders: [mswLoader()],
  parameters: {
    a11y: { test: "error" },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/i,
      },
    },
    docs: {
      codePanel: true,
    },
    layout: "centered",
  },
  tags: ["autodocs", "test"],
};

export default preview;
