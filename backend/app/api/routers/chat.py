from typing import List

from fastapi.responses import StreamingResponse

from app.utils.json import json_to_model
from app.utils.index import get_index
from app.utils.index import get_llm
from llama_index.llms import Ollama
from fastapi import APIRouter, Depends, HTTPException, Request, status
from llama_index import VectorStoreIndex
from llama_index.llms.base import MessageRole, ChatMessage
from pydantic import BaseModel

chat_router = r = APIRouter()


class _Message(BaseModel):
    role: MessageRole
    content: str


class _ChatData(BaseModel):
    messages: List[_Message]


@r.post("")
async def chat(
    request: Request,
    # Note: To support clients sending a JSON object using content-type "text/plain",
    # we need to use Depends(json_to_model(_ChatData)) here
    data: _ChatData = Depends(json_to_model(_ChatData)),
    index: VectorStoreIndex = Depends(get_index),
    llm:  Ollama = Depends(get_llm),
):
    # check preconditions and get last message
    if len(data.messages) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages provided",
        )
    lastMessage = data.messages.pop()
    if lastMessage.role != MessageRole.USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last message must be from user",
        )
    # convert messages coming from the request to type ChatMessage

    # create a list of messages
    messages = []

    # add the system message for llama2
    sys_message = ChatMessage(
            role="system", content="You are a helpful course assistant that answers the question based on the given \
            context. If the student asks a question that you don't know the answer to, \
            you can ask the student to rephrase the question. You can also ask the student to \
            provide more information about the question. If the student asks a question that is not about the \
            course, you can ask the student to ask the question in the correct channel. "
        )


    # set the index as retriever
    retriever = index.as_retriever(similarity_top_k=2)

    # retrieve the context from the question
    nodes = retriever.retrieve(lastMessage.content)
    
    # make the context
    context = ""
    for node in nodes:
        context = context + node.text + " "
    
    # create the user message with the context and question
    user_message = ChatMessage(
        role="user", content="CONTEXT: " + context + " QUESTION: " + lastMessage.content
    )

    # create the list of messages
    messages.append(sys_message)
    messages.append(user_message)

    # query chat engine
    #chat_engine = index.as_chat_engine()
    #response = chat_engine.stream_chat(lastMessage.content, messages)

    response = llm.stream_chat(messages)

    # stream response
    #async def event_generator():
    #    for token in response.response_gen:
    #        # If client closes connection, stop sending events
    #        if await request.is_disconnected():
    #            break
    #        yield token

    async def event_generator():
        for token in response:
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break
            yield token.delta

    return StreamingResponse(event_generator(), media_type="text/plain")
