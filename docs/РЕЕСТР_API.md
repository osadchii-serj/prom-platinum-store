# Реестр Prom.ua Public API

Источник: https://public-api.docs.prom.ua/documentation/index.yaml

Документов YAML: **93**. Операций: **35**.

Реестр составлен по документации; доступность методов для токена не проверена.
GET/HEAD/OPTIONS потенциально читают данные; эффекты остальных методов требуют проверки.

| Раздел | Метод | Путь | Описание | operationId |
|---|---|---|---|---|
| Chat | POST | /chat/mark_message_read | Change message status to read in the chat room | postMarkMessageRead |
| Chat | GET | /chat/messages_history | Get list of company chat messages | getChatMessages |
| Chat | GET | /chat/rooms | Get list of company chat rooms | getChatRooms |
| Chat | POST | /chat/send_attachments | Send attachments to the chat room | postChatAttachments |
| Chat | POST | /chat/send_file | Send file to the chat room | postChatFile |
| Chat | POST | /chat/send_message | Send message to the chat room | postChatMessage |
| Chat | POST | /chat/send_order_context | Send order context with message to the chat room | postSendOrderContext |
| Clients | GET | /clients/list | A list of the company's customers | getClientList |
| Clients | GET | /clients/{id} | Information about the customer | getClient |
| Delivery | POST | /delivery/save_declaration_id | Saving the declaration number | postDeliveryDeclarationId |
| Delivery | GET | /delivery_options/list | List of company shipping methods | getDeliveryOptionList |
| Groups | GET | /groups/list | List of company groups | getGroupList |
| Groups | PUT | /groups/translation | Translation of the group | putGroupTranslation |
| Groups | GET | /groups/translation/{id} | Translation of the group | getGroupTranslation |
| Messages | GET | /messages/list | List of company messages | getMessageList |
| Messages | POST | /messages/reply | Reply to message | postMessageReply |
| Messages | POST | /messages/set_status | Changing the status of the message(s) | postMessagesStatus |
| Messages | GET | /messages/{id} | Message information | getMessage |
| OrderStatus | GET | /order_status_options/list | List of company order statuses | getOrderStatusList |
| Orders | GET | /orders/list | List of company orders | getOrderList |
| Orders | POST | /orders/refund | Refund to buyer | postOrdersRefund |
| Orders | POST | /orders/set_status | Changing the status of the order(s) | postOrdersStatus |
| Orders | GET | /orders/{id} | Order information | getOrder |
| Orders | POST | /orders/{id}/attach_receipt | Attach receipt | postOrderAttachReceipt |
| Payment | GET | /payment_options/list | List of company payment methods | getPaymentOptionList |
| Products | GET | /products/by_external_id/{id} | Product information | getProductByExternalId |
| Products | POST | /products/edit | Product editing | postProductEdit |
| Products | POST | /products/edit_by_external_id | Editing products (by external identifier). | postProductEditByExternalId |
| Products | GET | /products/import/status/{id} | Import status | getProductsImportStatus |
| Products | POST | /products/import_file | Import of products | postProductsImportFile |
| Products | POST | /products/import_url | Import of products | postProductsImportURL |
| Products | GET | /products/list | List of company products | getProductList |
| Products | PUT | /products/translation | Product translation | putProductTranslation |
| Products | GET | /products/translation/{id} | Product translation | getProductTranslation |
| Products | GET | /products/{id} | Product information | getProduct |
