# Attention

These docs are now at End-of-Life and have been now moved to https://commcare-cloud.readthedocs.io/. The documentation files are now located in the `hosting_docs` directory. Any further modifications should happen in new docs. Pelase see the README.md in that directory to add or modify content.


# Testing the doc site locally

To test this doc site locally,
make sure you have the requirements installed as described
on Github's [Setting up your GitHub Pages site locally with Jekyll](https://help.github.com/articles/setting-up-your-github-pages-site-locally-with-jekyll/#requirements) article.

Then run from your local clone of `commcare-cloud`, run

```bash
cd docs
bundle install
```
 to install the dependencies and
 ```bash
 bundle exec jekyll serve
 ```
 to serve the doc site locally.

# Reference Material

- [Kramdown](https://kramdown.gettalong.org/documentation.html)
- [Conversion to HTML](https://kramdown.gettalong.org/converter/html.html)
