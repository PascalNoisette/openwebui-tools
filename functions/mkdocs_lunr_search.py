"""
title: Mkdocs lunr search
author: Pascal Noisette
git_url: https://github.com/PascalNoisette/openwebui-tools.git
version: 0.0.1
requirements: lunr
"""

import requests
from lunr import lunr
from typing import Callable, Any
import json
from pydantic import BaseModel


class Tools:
    def __init__(self):
        self.valves = self.Valves()
        pass

    class EventEmitter:
        def __init__(self, event_emitter: Callable[[dict], Any] = None):
            self.event_emitter = event_emitter

        async def emit(
            self, description="Unknown State", status="processing", done=False
        ):
            await self.event_emitter(
                {
                    "type": "status",
                    "data": {
                        "status": status,
                        "description": description,
                        "done": done,
                    },
                }
            )

    class Valves(BaseModel):
        base_url: str = "https://www.mkdocs.org/"
        login: str = ""
        password: str = ""

    async def search_blog(
        self, keyword: str, __event_emitter__: Callable[[dict], Any] = None
    ) -> str:
        """
        Please search for articles in a blog by keyword, to increase your knowledge.
        :param keyword: One or two words to represent a relevant topic from the prompt.
        :return: The relevant articles about the topic, or an error message.
        """

        context = []
        event = self.EventEmitter(__event_emitter__)
        url = self.valves.base_url.rstrip("/") + "/search/search_index.json"
        print(f"Searching blog '{url}' for '{keyword}'")
        await event.emit(f"Searching blog '{url}' for '{keyword}'")

        try:
            response = requests.get(url, auth=(self.valves.login, self.valves.password))
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            data = response.json()
            i = 0
            for doc in data["docs"]:
                doc["id"] = i
                i = i + 1
            await event.emit(f"Live index '{len(data['docs'])} documents'")
            idx = lunr(ref="id", fields=("title", "text"), documents=data["docs"])
            size = 0
            search = idx.search(keyword)
            for result in search:
                if size >= 3:
                    break
                size = size + 1
                doc = data["docs"][int(result["ref"])]
                context.append(doc)

                await __event_emitter__(
                    {
                        "type": "citation",
                        "data": {
                            "document": [doc["text"]],
                            "metadata": [
                                {
                                    "source": self.valves.base_url.rstrip("/")
                                    + "/"
                                    + doc["location"],
                                    "id": doc["id"],
                                    "title": doc["title"],
                                }
                            ],
                            "source": {"name": doc["title"]},
                        },
                    }
                )

            await event.emit(
                f"Found '{size} documents in blog '{url}' when searching for '{keyword}''",
                "success",
                True,
            )
        except Exception as e:
            await event.emit(f"Error searching blog: {str(e)}", "error", True)

        help = f"The following JSON contains relevant articles matching the topic '{keyword}' found in the blog. \n"
        return help + json.dumps(context, ensure_ascii=False)


if __name__ == "__main__":
    import asyncio, sys

    t = Tools()

    def emitter(*args, **kwargs):
        return asyncio.get_event_loop().run_in_executor(None, print, *args, **kwargs)

    print(asyncio.run(t.search_blog(sys.argv[1], emitter)))
